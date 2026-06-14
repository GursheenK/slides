<template>
	<div ref="slideContainer" class="flex size-full" @dragenter="showOverlay">
		<!-- when mounting place slide directly in the center of the visible container -->
		<!-- 1/2 width of viewport + 1/2 width of offset caused due to thinner navigation panel -->
		<div
			ref="slideRef"
			:style="slideStyles"
			:class="slideClasses"
			@contextmenu.prevent
			@dblclick="handleSlideDoubleClick"
		>
			<SelectionBox
				ref="selectionBox"
				v-if="!inReadonlyMode"
				:isDragging
				:elementOffset
				@mousedown="(e) => handleMouseDown(e)"
			/>

			<MarqueeOverlay v-if="!inReadonlyMode" @setIsSelecting="(val) => (isSelecting = val)" />

			<SnapGuides
				:ongoingInteraction="hasOngoingInteraction"
				:visibilityMap="visibilityMap"
			/>

			<SlideElement
				v-for="element in currentSlide?.elements"
				:key="`editor-${element.id}`"
				:ref="(comp) => registerElementDiv(element.id, comp?.$el)"
				mode="editor"
				:element
				:elementOffset
				:data-index="element.id"
				:highlight="highlightElement(element)"
				@mousedown="(e) => handleMouseDown(e, element)"
			/>
		</div>
		<DropTargetOverlay v-show="mediaDragOver" @hideOverlay="hideOverlay" />
		<OverflowContentOverlay />
	</div>
</template>

<script setup>
import {
	ref,
	computed,
	watch,
	useTemplateRef,
	nextTick,
	onMounted,
	onBeforeUnmount,
	provide,
	reactive,
	onActivated,
	onDeactivated,
	inject,
} from 'vue'
import { useResizeObserver } from '@vueuse/core'

import SnapGuides from '@/components/SnapGuides.vue'
import SelectionBox from '@/components/SelectionBox.vue'
import MarqueeOverlay from '@/components/MarqueeOverlay.vue'
import SlideElement from '@/components/SlideElement.vue'
import DropTargetOverlay from '@/components/DropTargetOverlay.vue'
import OverflowContentOverlay from '@/components/OverflowContentOverlay.vue'

import {
	currentSlide,
	slideBounds,
	selectionBounds,
	updateSelectionBounds,
	slideIndex,
} from '@/stores/slide'

import {
	activeElementIds,
	activeElement,
	focusElementId,
	pairElementId,
	addFixedWidthToElement,
	setEditableState,
	duplicateElements,
	activeElements,
	addTextElement,
	cropSelectionToFitContent,
} from '@/stores/element'

import { commandHistory } from '@/stores/historyMeta'

import { handleCopy, handlePaste } from '@/stores/copyPaste'

import { registerElementDiv, getElementDiv } from '@/stores/elementRegistry'

import { useDragAndDrop } from '@/composables/useDragAndDrop'
import { useResizer } from '@/composables/useResizer'
import { useRotator } from '@/composables/useRotator'
import { usePanAndZoom } from '@/composables/usePanAndZoom'
import { useSnapping } from '@/composables/useSnapping'
import { editElementCommand, batchCommand } from '@/stores/commands'

import { isCmdOrCtrl } from '@/utils/helpers'
import { minElementSizes } from '@/utils/constants'

const props = defineProps({
	highlight: Boolean,
})

const emit = defineEmits(['update:hasOngoingInteraction'])

const inReadonlyMode = inject('inReadonlyMode', ref(false))

const slideContainerRef = useTemplateRef('slideContainer')
const slideRef = useTemplateRef('slideRef')
const selectionBoxRef = useTemplateRef('selectionBox')

const { isDragging, positionDelta, startDragging } = useDragAndDrop()

const { isResizing, dimensionDelta, currentResizer, resizeCursor, startResize } = useResizer()

const { isRotating, rotationDelta, startRotate, resetRotation } = useRotator()

const hasOngoingInteraction = computed(
	() => isDragging.value || isResizing.value || isRotating.value,
)

const { visibilityMap, applySnapping } = useSnapping(
	selectionBoxRef,
	slideRef,
	currentResizer,
	hasOngoingInteraction,
)

const { allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(slideContainerRef, slideRef)

const slideClasses = computed(() => {
	const classes = ['absolute', 'h-[540px]', 'w-[960px]', 'shadow-2xl', 'shadow-gray-400']

	const outlineClasses =
		props.highlight || mediaDragOver.value ? ['outline', 'outline-2', 'outline-blue-400'] : []

	const positionClasses = inReadonlyMode.value
		? ['left-[calc(50%-384.5px)]', 'top-[calc(50%-270px)]']
		: ['left-[calc(50%-512px)]', 'top-[calc(50%-270px)]']

	return [...classes, outlineClasses, positionClasses]
})

const isSelecting = ref(false)

const getSlideCursor = () => {
	if (isDragging.value) return 'move'
	if (isSelecting.value) return 'crosshair'
	if (resizeCursor.value) return resizeCursor.value

	return 'default'
}

const highlightElement = (element) => {
	const toHighlight =
		activeElementIds.value.length > 1 && activeElementIds.value.includes(element.id)
	return toHighlight || pairElementId.value == element.id
}

const slideStyles = computed(() => ({
	transformOrigin: transformOrigin.value,
	transform: transform.value,
	backgroundColor: currentSlide.value?.background || '#ffffff',
	cursor: getSlideCursor(),
	zIndex: 0,
}))

const mediaDragOver = ref(false)

const showOverlay = (e) => {
	e.preventDefault()
	if (inReadonlyMode.value) return
	mediaDragOver.value = true
}

const hideOverlay = () => {
	mediaDragOver.value = false
}

const triggerSelection = (e, id) => {
	if (id) {
		if (!activeElementIds.value.includes(id)) {
			if (isCmdOrCtrl(e) || e.shiftKey) {
				activeElementIds.value = [...activeElementIds.value, id]
			} else activeElementIds.value = [id]
			focusElementId.value = null
		} else if (activeElement.value?.type == 'text') {
			focusElementId.value = id

			setEditableState()
		}
	}
}

const handleMouseUp = (e, id) => {
	pairElementId.value = null

	if (!isDragging.value) triggerSelection(e, id)
}

const triggerDrag = (e, id) => {
	const notEditable = id && focusElementId.value !== id
	const isMultiSelect = activeElementIds.value.length > 1
	const isNotInSelection = id && !activeElementIds.value.includes(id)

	// prevent drag if multiple are selected and id isn't in the selection
	if (isMultiSelect && isNotInSelection) return

	if (notEditable || isMultiSelect) {
		startDragging(e)

		if (id && !isMultiSelect && activeElementIds.value[0] !== id) {
			activeElementIds.value = [id]
			focusElementId.value = null

			// the selection watcher will crop async — too late for the drag
			// anchor below, so fit the bounds to this element now
			cropSelectionToFitContent([id])
		}

		// anchor synchronously: the drag math must never depend on watcher
		// flush order or on a previous gesture's state
		dragAnchor = {
			left: selectionBounds.left,
			top: selectionBounds.top,
		}
	}
}

const DRAG_START_THRESHOLD = 4

const watchForDragIntent = (downEvent, id) => {
	const cancelDragIntent = () => {
		window.removeEventListener('mousemove', detectDrag)
		window.removeEventListener('mouseup', cancelDragIntent)
	}

	const detectDrag = (moveEvent) => {
		// button already released (e.g. mouseup outside the window)
		if (!moveEvent.buttons) return cancelDragIntent()

		const dx = moveEvent.clientX - downEvent.clientX
		const dy = moveEvent.clientY - downEvent.clientY
		if (Math.hypot(dx, dy) < DRAG_START_THRESHOLD) return

		cancelDragIntent()

		// pass the original mousedown event so the drag measures
		// from the press position and no movement is lost
		triggerDrag(downEvent, id)
	}

	window.addEventListener('mousemove', detectDrag)
	window.addEventListener('mouseup', cancelDragIntent)
}

const duplicateAndDrag = (e, id) => {
	duplicateElements(e, activeElements.value, slideIndex.value, false).then(() => {
		watchForDragIntent(e, id)
	})
}

const handleMouseDown = (e, element) => {
	if (inReadonlyMode.value) return
	const id = element?.id

	e.stopPropagation()
	e.preventDefault()

	if (e.altKey || e.ctrlKey) return duplicateAndDrag(e, id)

	// start dragging once the pointer moves past a small threshold
	watchForDragIntent(e, id)

	// if mouseup happens before the threshold is crossed
	// then consider it a selection instead of dragging
	e.target.addEventListener('mouseup', () => handleMouseUp(e, id), { once: true })
}

const scale = computed(() => {
	const matrix = transform.value?.match(/matrix\((.+)\)/)
	if (!matrix) return 1
	return parseFloat(matrix[1].split(', ')[0])
})

const activeDiv = computed(() => {
	if (activeElementIds.value.length != 1) return null
	return getElementDiv(activeElementIds.value[0])
})

useResizeObserver(activeDiv, (entries) => {
	const entry = entries[0]
	const { width, height } = entry.contentRect

	// fires on any size change: resize gestures, and property updates like
	// font size / line height / letter spacing

	// shapes/images are layout-anchored: left/top derive from element state,
	// no forced-layout read needed
	if (['shape', 'image'].includes(activeElement.value?.type)) {
		updateSelectionBounds({
			width: width,
			height: height,
			left: activeElement.value.left + elementOffset.left,
			top: activeElement.value.top + elementOffset.top,
		})
		return
	}

	// text elements are center-anchored (translate(-50%, -50%)): their visual
	// left/top shift whenever the size changes, so read the rendered rect
	const target = entry.target.getBoundingClientRect()

	updateSelectionBounds({
		width: width,
		height: height,
		left: (target.left - slideBounds.left) / scale.value,
		top: (target.top - slideBounds.top) / scale.value,
	})
})

const togglePanZoom = () => {
	allowPanAndZoom.value = !allowPanAndZoom.value
}

const elementOffset = reactive({
	left: 0,
	top: 0,
	width: 0,
	height: 0,
})

// selection bounds at drag start — captured synchronously in triggerDrag
let dragAnchor = null

const handlePositionChange = (total) => {
	if (!dragAnchor) return

	// snap the desired (cursor-anchored) position, then correct toward it —
	// the element sits wherever the snapped desired geometry says, so it can
	// never drift from the cursor
	const desired = applySnapping(
		{
			left: dragAnchor.left + total.left / slideBounds.scale,
			top: dragAnchor.top + total.top / slideBounds.scale,
			width: selectionBounds.width,
			height: selectionBounds.height,
		},
		'dragging',
	)

	const delta = {
		left: (desired.left - selectionBounds.left) * slideBounds.scale,
		top: (desired.top - selectionBounds.top) * slideBounds.scale,
	}

	if (!delta.left && !delta.top) return

	applyPositionDelta(delta)
}

const CORNER_RESIZERS = ['top-left', 'top-right', 'bottom-left', 'bottom-right']

// media corners lock aspect: rendered height follows width through layout,
// so the cursor's Y axis is discarded and top derives from the width delta
const applyAspectRatio = (delta) => {
	if (!CORNER_RESIZERS.includes(currentResizer.value)) return

	const ratio = selectionBounds.width / selectionBounds.height

	delta.height = 0
	delta.top = ['top-left', 'top-right'].includes(currentResizer.value) ? -delta.width / ratio : 0
}

const getMinSizes = () => {
	return minElementSizes[activeElement.value?.type] ?? minElementSizes.default
}

// live size during a gesture (selectionBounds lag a frame behind the observer)
const getCurrentSize = () => ({
	width: (activeElement.value?.width ?? selectionBounds.width) + elementOffset.width,
	height: (activeElement.value?.height ?? selectionBounds.height) + elementOffset.height,
})

// fraction (0..1) of a shrink that fits above the minimum; growing always fits
const allowedShrinkFraction = (deltaPx, current, min) => {
	if (deltaPx >= 0) return 1

	const requestedShrink = -deltaPx / slideBounds.scale
	return Math.min(1, Math.max(0, (current - min) / requestedShrink))
}

// clamp each axis at its minimum, scaling the linked position delta with it —
// clamping size alone would let the element slide while pinned
const clampToMinSizes = (delta) => {
	const min = getMinSizes()
	const size = getCurrentSize()

	const widthFactor = allowedShrinkFraction(delta.width, size.width, min.width)
	const heightFactor = allowedShrinkFraction(delta.height, size.height, min.height)

	delta.width *= widthFactor
	delta.left *= widthFactor

	delta.height *= heightFactor

	// media corner top derives from width (aspect lock); otherwise top
	// belongs to the height axis
	const topFollowsWidth = ['image', 'video'].includes(activeElement.value?.type)
	delta.top *= topFollowsWidth ? widthFactor : heightFactor
}

const applyPositionDelta = (delta) => {
	if (!delta.left && !delta.top) return

	const deltaLeft = delta.left / slideBounds.scale
	const deltaTop = delta.top / slideBounds.scale

	updateSelectionBounds({
		left: selectionBounds.left + deltaLeft,
		top: selectionBounds.top + deltaTop,
	})

	elementOffset.left += deltaLeft
	elementOffset.top += deltaTop
}

const applyDimensionDelta = (delta) => {
	if (!delta.width && !delta.height) return

	const deltaWidth = delta.width / slideBounds.scale
	const deltaHeight = delta.height / slideBounds.scale

	elementOffset.width += deltaWidth
	elementOffset.height += deltaHeight
}

// selection bounds + dimensions at resize start — captured synchronously in
// startElementResize, same rule as the drag anchor
let resizeAnchor = null

const startElementResize = (e, resizer) => {
	resizeAnchor = {
		left: selectionBounds.left,
		top: selectionBounds.top,
		width: selectionBounds.width,
		height: selectionBounds.height,
	}

	startResize(e, resizer)
}

const handleDimensionChange = (total) => {
	if (!resizeAnchor) return

	const scale = slideBounds.scale
	const size = getCurrentSize()

	const isMedia = ['image', 'video'].includes(activeElement.value.type)

	// snap the desired (cursor-anchored) geometry, then correct toward it —
	// same model as drag, so the handle can never drift from the cursor.
	// media only snap their width edges: height/top derive from aspect below
	const desired = applySnapping(
		{
			left: resizeAnchor.left + total.left / scale,
			top: resizeAnchor.top + total.top / scale,
			width: resizeAnchor.width + total.width / scale,
			height: resizeAnchor.height + total.height / scale,
		},
		'resizing',
		{ axes: isMedia ? ['x'] : ['x', 'y'] },
	)

	const delta = {
		width: (desired.width - size.width) * scale,
		height: (desired.height - size.height) * scale,
		left: (desired.left - selectionBounds.left) * scale,
		top: (desired.top - selectionBounds.top) * scale,
	}

	if (!delta.width && !delta.height && !delta.left && !delta.top) return

	if (isMedia) applyAspectRatio(delta)

	clampToMinSizes(delta)

	applyPositionDelta(delta)

	if (!activeElement.value.width) addFixedWidthToElement()

	applyDimensionDelta(delta)
}

const updateSlideBounds = () => {
	const slideRect = slideRef.value.getBoundingClientRect()

	slideBounds.width = slideRect.width
	slideBounds.height = slideRect.height
	slideBounds.left = slideRect.left
	slideBounds.top = slideRect.top
	slideBounds.scale = scale.value
}

const handleSlideTransform = () => {
	// wait for the new transform to render before updating dimensions
	nextTick(() => {
		updateSlideBounds()
	})
}

watch(
	() => activeElementIds.value,
	(newVal, oldVal) => {
		selectionBoxRef.value?.handleSelectionChange(newVal, oldVal)
	},
)

watch(
	() => transform.value,
	() => {
		if (!transform.value) return
		handleSlideTransform()
	},
)

watch(
	() => positionDelta.value,
	(total) => {
		handlePositionChange(total)
	},
)

watch(
	() => dimensionDelta.value,
	(delta) => {
		handleDimensionChange(delta)
	},
)

const initSlideAndListeners = () => {
	if (!slideRef.value) return

	updateSlideBounds()

	document.addEventListener('copy', handleCopy)
	document.addEventListener('paste', handlePaste)
	window.addEventListener('resize', updateSlideBounds)
}

const clearListeners = () => {
	document.removeEventListener('copy', handleCopy)
	document.removeEventListener('paste', handlePaste)
	window.removeEventListener('resize', updateSlideBounds)
}

onMounted(() => initSlideAndListeners())

onActivated(() => initSlideAndListeners())

onDeactivated(() => clearListeners())

onBeforeUnmount(() => clearListeners())

provide('slideDiv', slideRef)
provide('slideContainerDiv', slideContainerRef)
provide('resizer', {
	currentResizer,
	startResize: startElementResize,
})
provide('rotator', {
	startRotate,
})

defineExpose({
	togglePanZoom,
})

const getInteractionCommands = () => {
	const commands = []

	activeElementIds.value.forEach((id) => {
		const element = currentSlide.value.elements.find((el) => el.id === id)
		if (!element) return

		const createCommand = (property, oldValue, newValue) => {
			if (newValue == oldValue) return null
			return editElementCommand({
				slideId: currentSlide.value.clientId,
				elementIds: [id],
				property,
				oldValue,
				newValue,
			})
		}

		const offsetKeys = ['left', 'top', 'width', 'height']

		offsetKeys.forEach((key) => {
			if (elementOffset[key]) {
				const oldValue = element[key]
				const newValue = element[key] + elementOffset[key]

				const command = createCommand(key, oldValue, newValue)

				if (command) commands.push(command)
			}
		})

		if (rotationDelta.value && ['shape', 'image'].includes(element.type)) {
			const oldValue = element.rotation || 0
			const newValue = oldValue + rotationDelta.value
			const command = createCommand('rotation', oldValue, newValue)

			if (command) commands.push(command)
		}
	})

	return commands
}

const applyInteractionOffsets = () => {
	pairElementId.value = null
	requestAnimationFrame(() => {
		const commands = getInteractionCommands()

		commandHistory.execute(
			batchCommand({
				slideId: currentSlide.value.clientId,
				elementIds: activeElementIds.value,
				commands,
			}),
		)

		elementOffset.left = 0
		elementOffset.top = 0
		elementOffset.width = 0
		elementOffset.height = 0
		resetRotation()
	})
}

watch(
	() => hasOngoingInteraction.value,
	(newVal, oldVal) => {
		if (oldVal && !newVal) applyInteractionOffsets()
		emit('update:hasOngoingInteraction', newVal)
	},
)

const handleSlideDoubleClick = (e) => {
	if (inReadonlyMode.value || e.target !== e.currentTarget) return
	addTextElement('', {
		left: (e.clientX - slideBounds.left) / scale.value,
		top: (e.clientY - slideBounds.top) / scale.value,
	})
}
</script>

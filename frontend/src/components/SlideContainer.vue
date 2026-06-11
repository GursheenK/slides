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

const { visibilityMap, resistanceMap, handleSnapping } = useSnapping(
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

const applyResistance = (axis, delta) => {
	const scaledThreshold = (0.01 * selectionBounds.width) / slideBounds.scale

	const escapeDelta = Math.max(1.5, Math.min(5, scaledThreshold))

	let useResistanceKeys = []
	let pullDelta = null

	if (axis == 'X') {
		useResistanceKeys = ['left', 'right', 'centerY']
		pullDelta = delta.left
	} else if (axis == 'Y') {
		useResistanceKeys = ['top', 'bottom', 'centerX']
		pullDelta = delta.top
	} else if (axis == null && currentResizer.value) {
		useResistanceKeys = ['left', 'right', 'top', 'bottom', 'centerX', 'centerY']
		pullDelta = delta.width
	}

	const useResistance = useResistanceKeys.some((key) => resistanceMap[key])

	return useResistance && Math.abs(pullDelta) < escapeDelta
}

const updateTotalDeltaForResize = (totalDelta, delta, width, height) => {
	totalDelta.width = applyResistance(null, delta) ? 0 : width
	totalDelta.height = applyResistance(null, delta) ? 0 : height

	// if resisting width change, don't apply top change either otherwise
	// element sticks to one axis and drags on other which shouldn't happen on resize
	if (totalDelta.width === 0 && !['top', 'bottom'].includes(currentResizer.value)) {
		totalDelta.top = 0
	}
}

const getTotalInteractionDelta = (delta, interaction = 'dragging') => {
	const snapDelta = handleSnapping(interaction)

	const left = snapDelta.x || delta.left
	const top = snapDelta.y || delta.top

	const totalDelta = {
		left: applyResistance('X', delta) ? 0 : left,
		top: applyResistance('Y', delta) ? 0 : top,
	}

	const width = snapDelta.width || delta.width
	const height = snapDelta.height || delta.height

	if (interaction === 'resizing') {
		updateTotalDeltaForResize(totalDelta, delta, width, height)
	}

	return totalDelta
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

	const desiredLeft = dragAnchor.left + total.left / slideBounds.scale
	const desiredTop = dragAnchor.top + total.top / slideBounds.scale

	// correction toward the cursor-anchored position: snapping and resistance
	// may withhold or replace it this frame, but the next frame re-measures
	// against the cursor, so the element can never permanently drift
	const delta = {
		left: (desiredLeft - selectionBounds.left) * slideBounds.scale,
		top: (desiredTop - selectionBounds.top) * slideBounds.scale,
	}

	if (!delta.left && !delta.top) return

	const totalDelta = getTotalInteractionDelta(delta)

	applyPositionDelta(totalDelta)
}

const applyAspectRatio = (delta, type) => {
	if (!['top-left', 'top-right', 'bottom-left', 'bottom-right'].includes(currentResizer.value))
		return

	if (type == 'shape') {
		delta.height = delta.width
	}

	if (!delta.top || !['image', 'video'].includes(type)) return
	const ratio = selectionBounds.width / selectionBounds.height
	delta.top = (delta.top ?? 0) / ratio
}

const validateMinWidth = (width) => {
	const minWidth = activeElement.value?.type === 'text' ? 7 : 1
	return width + selectionBounds.width > minWidth
}

const validateMinHeight = (height) => {
	const minHeight = activeElement.value?.type === 'text' ? 7 : 29
	return height + selectionBounds.height > minHeight
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

const handleDimensionChange = (delta) => {
	if (!delta.width && !delta.height) return
	if (!validateMinWidth(delta.width)) delta.width = 0
	if (!validateMinHeight(delta.height)) delta.height = 0

	if (['shape', 'image', 'video'].includes(activeElement.value.type)) {
		applyAspectRatio(delta, activeElement.value.type)
	}

	const totalDelta = getTotalInteractionDelta(delta, 'resizing')

	applyPositionDelta(totalDelta)

	if (!activeElement.value.width) addFixedWidthToElement()

	applyDimensionDelta(totalDelta)
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
	startResize,
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

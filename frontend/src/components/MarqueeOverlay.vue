<template>
	<div v-if="isSelecting" :style="marqueeStyles"></div>
</template>
<script setup>
import { ref, reactive, computed, inject, onMounted, onBeforeUnmount } from 'vue'

import { currentSlide, slideBounds } from '@/stores/slide'
import {
	activeElementIds,
	setActiveElements,
	getElementPosition,
	resetFocus,
	isWithinOverlappingBounds,
} from '@/stores/element'

const slideDiv = inject('slideDiv')
const slideContainerDiv = inject('slideContainerDiv')

const emit = defineEmits(['setIsSelecting'])

const SELECTION_START_THRESHOLD = 4

const isSelecting = ref(false)

const marqueeRect = reactive({
	left: 0,
	top: 0,
	width: 0,
	height: 0,
})

let startX = 0
let startY = 0

const marqueeStyles = computed(() => ({
	position: 'absolute',
	backgroundColor: '#70b6f025',
	outline: `#70B6F092 solid ${0.1 / slideBounds.scale}px`,
	width: `${marqueeRect.width}px`,
	height: `${marqueeRect.height}px`,
	left: `${marqueeRect.left}px`,
	top: `${marqueeRect.top}px`,
	boxSizing: 'border-box',
	zIndex: 9999,
	pointerEvents: 'none',
}))

const toSlideCoords = (e) => ({
	x: (e.clientX - slideBounds.left) / slideBounds.scale,
	y: (e.clientY - slideBounds.top) / slideBounds.scale,
})

const initSelection = (e) => {
	// drawing a marquee always starts from an empty selection
	activeElementIds.value = []

	isSelecting.value = true
	emit('setIsSelecting', true)

	const { x, y } = toSlideCoords(e)
	startX = x
	startY = y

	Object.assign(marqueeRect, { left: x, top: y, width: 0, height: 0 })

	document.addEventListener('mousemove', updateSelection)
	document.addEventListener('mouseup', endSelection, { once: true })
}

const updateSelection = (e) => {
	const { x, y } = toSlideCoords(e)

	marqueeRect.left = Math.min(x, startX)
	marqueeRect.top = Math.min(y, startY)
	marqueeRect.width = Math.abs(x - startX)
	marqueeRect.height = Math.abs(y - startY)
}

const getElementsWithinMarquee = () => {
	const marqueeBounds = {
		left: marqueeRect.left,
		top: marqueeRect.top,
		right: marqueeRect.left + marqueeRect.width,
		bottom: marqueeRect.top + marqueeRect.height,
	}

	const elements = []

	currentSlide.value.elements.forEach((element) => {
		const elementPosition = getElementPosition(element.id)

		if (isWithinOverlappingBounds(marqueeBounds, elementPosition)) {
			elements.push(element.id)
		}
	})

	return elements
}

const endSelection = () => {
	isSelecting.value = false
	emit('setIsSelecting', false)

	document.removeEventListener('mousemove', updateSelection)

	const selectedElements = getElementsWithinMarquee()
	if (selectedElements.length) setActiveElements(selectedElements)

	Object.assign(marqueeRect, { left: 0, top: 0, width: 0, height: 0 })
}

let cancelSelectionIntent = null

const watchForSelectionIntent = (downEvent) => {
	const detectSelection = (moveEvent) => {
		// button already released (e.g. mouseup outside the window)
		if (!moveEvent.buttons) return cancelSelectionIntent?.()

		const dx = moveEvent.clientX - downEvent.clientX
		const dy = moveEvent.clientY - downEvent.clientY
		if (Math.hypot(dx, dy) < SELECTION_START_THRESHOLD) return

		cancelSelectionIntent?.()

		// anchor the marquee at the press position
		initSelection(downEvent)
	}

	const deselectOnRelease = (upEvent) => {
		cancelSelectionIntent?.()
		selectSlide(upEvent)
	}

	cancelSelectionIntent = () => {
		document.removeEventListener('mousemove', detectSelection)
		document.removeEventListener('mouseup', deselectOnRelease)
		cancelSelectionIntent = null
	}

	document.addEventListener('mousemove', detectSelection)
	document.addEventListener('mouseup', deselectOnRelease)
}

const handleMouseDown = (e) => {
	// marquee / deselect only start from the empty slide or container area
	if (![slideDiv.value, slideContainerDiv.value].includes(e.target)) return

	watchForSelectionIntent(e)
}

const selectSlide = (e) => {
	e.preventDefault()
	e.stopPropagation()
	resetFocus()
}

onMounted(() => {
	document.addEventListener('mousedown', handleMouseDown)
})

onBeforeUnmount(() => {
	cancelSelectionIntent?.()
	document.removeEventListener('mousedown', handleMouseDown)
	document.removeEventListener('mousemove', updateSelection)
	document.removeEventListener('mouseup', endSelection)
})
</script>

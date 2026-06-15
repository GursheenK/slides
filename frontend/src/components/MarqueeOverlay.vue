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
import { getElementDiv } from '@/stores/elementRegistry'

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

const getRotatedRectCorners = (center, halfWidth, halfHeight, rotation) => {
	const radians = (rotation * Math.PI) / 180
	const cos = Math.cos(radians)
	const sin = Math.sin(radians)

	const cornerAt = (x, y) => ({
		x: center.x + x * cos - y * sin,
		y: center.y + x * sin + y * cos,
	})

	return [
		cornerAt(-halfWidth, -halfHeight),
		cornerAt(halfWidth, -halfHeight),
		cornerAt(halfWidth, halfHeight),
		cornerAt(-halfWidth, halfHeight),
	]
}

const getRectCorners = (bounds) => [
	{ x: bounds.left, y: bounds.top },
	{ x: bounds.right, y: bounds.top },
	{ x: bounds.right, y: bounds.bottom },
	{ x: bounds.left, y: bounds.bottom },
]

const getProjectedSpan = (corners, axis) => {
	const distances = corners.map((corner) => corner.x * axis.x + corner.y * axis.y)
	return { min: Math.min(...distances), max: Math.max(...distances) }
}

const spansOverlap = (a, b) => a.min <= b.max && b.min <= a.max

const rectsOverlap = (cornersA, cornersB, axes) =>
	axes.every((axis) =>
		spansOverlap(getProjectedSpan(cornersA, axis), getProjectedSpan(cornersB, axis)),
	)

// a rotated element's bounding box is mostly empty space, so test the marquee
// against the element's actual rotated rectangle instead.
const isRotatedElementWithinMarquee = (element, marqueeBounds) => {
	const div = getElementDiv(element.id)
	if (!div) return false

	// the rotated rect shares its centre with the axis-aligned bounding box
	const boundingBox = getElementPosition(element.id)
	const center = {
		x: (boundingBox.left + boundingBox.right) / 2,
		y: (boundingBox.top + boundingBox.bottom) / 2,
	}

	const elementCorners = getRotatedRectCorners(
		center,
		div.offsetWidth / 2,
		div.offsetHeight / 2,
		element.rotation,
	)
	const marqueeCorners = getRectCorners(marqueeBounds)

	// the marquee's edges run along x/y; the element's run along its rotated axes
	const radians = (element.rotation * Math.PI) / 180
	const elementAxis = { x: Math.cos(radians), y: Math.sin(radians) }
	const axes = [
		{ x: 1, y: 0 },
		{ x: 0, y: 1 },
		elementAxis,
		{ x: -elementAxis.y, y: elementAxis.x },
	]

	return rectsOverlap(elementCorners, marqueeCorners, axes)
}

const isElementWithinMarquee = (element, marqueeBounds) => {
	if (element.rotation) return isRotatedElementWithinMarquee(element, marqueeBounds)
	return isWithinOverlappingBounds(marqueeBounds, getElementPosition(element.id))
}

const getElementsWithinMarquee = () => {
	const marqueeBounds = {
		left: marqueeRect.left,
		top: marqueeRect.top,
		right: marqueeRect.left + marqueeRect.width,
		bottom: marqueeRect.top + marqueeRect.height,
	}

	return currentSlide.value.elements
		.filter((element) => isElementWithinMarquee(element, marqueeBounds))
		.map((element) => element.id)
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

<template>
	<!-- Capture layer: covers the whole slide so all mouse events go here during draw mode -->
	<div
		v-if="pendingShapeType"
		style="position: absolute; inset: 0; cursor: crosshair; z-index: 10000"
		@mousedown.prevent="handleMouseDown"
	/>
	<!-- Live preview of the shape being drawn -->
	<div v-if="isDrawing" :style="previewStyles" />
</template>
<script setup>
import { computed, onMounted, onBeforeUnmount } from 'vue'

import { pendingShapeType, addShapeElement } from '@/stores/element'
import { slideBounds } from '@/stores/slide'
import { useDrawRect } from '@/composables/useDrawRect'

const { isDrawing, drawRect, startPoint, endPoint, startDrawing, cancel } = useDrawRect()

const MIN_SIZE = 10

const isLine = computed(
	() => pendingShapeType.value === 'line' || pendingShapeType.value === 'line with arrows',
)

const previewBorderRadius = computed(() => {
	if (pendingShapeType.value === 'circle') return '50%'
	if (['rounded rectangle', 'rounded square'].includes(pendingShapeType.value)) return '8px'
	return '0'
})

const linePreviewStyles = computed(() => {
	const { x: x1, y: y1 } = startPoint
	const { x: x2, y: y2 } = endPoint
	const dx = x2 - x1
	const dy = y2 - y1
	const length = Math.sqrt(dx ** 2 + dy ** 2)
	const angle = Math.atan2(dy, dx) * (180 / Math.PI)

	return {
		position: 'absolute',
		left: `${x1}px`,
		top: `${y1}px`,
		width: `${length}px`,
		height: `${Math.max(2 / slideBounds.scale, 2)}px`,
		transformOrigin: '0 50%',
		transform: `translate(0, -50%) rotate(${angle}deg)`,
		backgroundColor: '#70B6F092',
		zIndex: 10001,
		pointerEvents: 'none',
	}
})

const previewStyles = computed(() => {
	if (isLine.value) return linePreviewStyles.value

	const { left, top, width, height } = drawRect
	return {
		position: 'absolute',
		left: `${left}px`,
		top: `${top}px`,
		width: `${width}px`,
		height: `${height}px`,
		backgroundColor: '#70b6f025',
		outline: `#70B6F092 solid ${0.1 / slideBounds.scale}px`,
		borderRadius: previewBorderRadius.value,
		boxSizing: 'border-box',
		zIndex: 10001,
		pointerEvents: 'none',
	}
})

const handleMouseDown = (e) => {
	startDrawing(e, (rect, p1, p2) => {
		const bounds = isLine.value ? { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y } : rect
		const isBigEnough = isLine.value
			? Math.hypot(p2.x - p1.x, p2.y - p1.y) >= MIN_SIZE
			: rect.width >= MIN_SIZE && rect.height >= MIN_SIZE

		if (isBigEnough) addShapeElement(pendingShapeType.value, bounds)
		pendingShapeType.value = null
	})
}

const handleKeyDown = (e) => {
	if (e.key === 'Escape' && pendingShapeType.value) {
		cancel()
		pendingShapeType.value = null
	}
}

onMounted(() => document.addEventListener('keydown', handleKeyDown))
onBeforeUnmount(() => {
	document.removeEventListener('keydown', handleKeyDown)
	cancel()
})
</script>

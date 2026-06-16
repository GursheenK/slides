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

const { isDrawing, drawRect, startDrawing, cancel } = useDrawRect()

const MIN_SIZE = 10

const isLine = computed(
	() => pendingShapeType.value === 'line' || pendingShapeType.value === 'line with arrows',
)

const previewBorderRadius = computed(() => {
	if (pendingShapeType.value === 'circle') return '50%'
	if (['rounded rectangle', 'rounded square'].includes(pendingShapeType.value)) return '8px'
	return '0'
})

const previewStyles = computed(() => {
	const { left, top, width } = drawRect
	// Lines always render at a fixed thin height regardless of how far the mouse moved vertically
	const height = isLine.value ? Math.max(2 / slideBounds.scale, 2) : drawRect.height

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
	startDrawing(e, (finalRect) => {
		const tooSmall = isLine.value
			? finalRect.width < MIN_SIZE
			: finalRect.width < MIN_SIZE || finalRect.height < MIN_SIZE

		if (!tooSmall) addShapeElement(pendingShapeType.value, finalRect)

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

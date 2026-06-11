<template>
	<div v-show="selectionBounds.width" ref="selected" :style="boxStyles">
		<Resizer
			v-if="showResizers"
			:elementType="activeElement?.shapeType || activeElement?.type"
			:dimensions="selectionBounds"
			:style="{ pointerEvents: 'auto' }"
		/>
	</div>
</template>
<script setup>
import { computed, useTemplateRef } from 'vue'

import Resizer from '@/components/Resizer.vue'

import { slideBounds, selectionBounds, updateSelectionBounds } from '@/stores/slide'
import {
	activeElementIds,
	focusElementId,
	activeElement,
	cropSelectionToFitContent,
} from '@/stores/element'

const props = defineProps({
	isDragging: {
		type: Boolean,
		default: false,
	},
	rotationDelta: {
		type: Number,
		default: 0,
	},
})

const selectedRef = useTemplateRef('selected')

const showResizers = computed(() => {
	return activeElementIds.value.length == 1 && !focusElementId.value && !props.isDragging
})

const outline = computed(() => {
	if (activeElement.value?.shapeType == 'line') return 'none'

	if (activeElementIds.value.length == 1) return `#70B6F0 solid ${2 / slideBounds.scale}px`
	return `#70B6F092 solid ${0.1 / slideBounds.scale}px`
})

const isRotatable = computed(() => {
	return ['shape', 'image'].includes(activeElement.value?.type)
})

const selectionRotation = computed(() => {
	if (activeElementIds.value.length != 1 || !isRotatable.value) return 0
	return (activeElement.value.rotation || 0) + props.rotationDelta
})

const boxStyles = computed(() => ({
	position: 'absolute',
	backgroundColor: activeElementIds.value.length == 1 ? '' : '#70b6f025',
	outline: outline.value,
	width: `${selectionBounds.width}px`,
	height: `${selectionBounds.height}px`,
	left: `${selectionBounds.left}px`,
	top: `${selectionBounds.top}px`,
	boxSizing: 'border-box',
	zIndex: 9999,
	pointerEvents: activeElementIds.value.length == 1 ? 'none' : 'auto',
	transform: selectionRotation.value ? `rotate(${selectionRotation.value}deg)` : '',
	transformOrigin: 'center center',
}))

const resetSelection = (oldVal) => {
	updateSelectionBounds({
		width: 0,
		height: 0,
		left: 0,
		top: 0,
	})
}

const handleSelection = (elementIds) => {
	if (!elementIds.length) return
	cropSelectionToFitContent(elementIds)
}

const handleSelectionChange = (elementIds, oldIds) => {
	resetSelection(oldIds)
	handleSelection(elementIds)
}

defineExpose({
	handleSelectionChange,
})
</script>

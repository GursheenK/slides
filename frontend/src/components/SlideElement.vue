<template>
	<div ref="slideElement" :style="elementStyle">
		<component
			:is="getDynamicComponent(element.type)"
			:element="element"
			@select="selectElement"
			@focus="focusOnElement"
			@mousedown="handleMouseDown"
			@mouseup="handleMouseUp"
		/>
	</div>
</template>

<script setup>
import { computed, inject, nextTick, ref, useTemplateRef, watch } from 'vue'
import { useDragAndDrop } from '@/utils/drag'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'

import {
	activeElementIds,
	pairElementId,
	focusElementId,
	setActiveElements,
	activeElement,
} from '@/stores/element'
import { inSlideShow } from '@/stores/presentation'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const outline = computed(() => {
	if (
		activeElementIds.value.concat([focusElementId.value]).includes(element.value.id) ||
		isDragging.value
	)
		return '#70B6F0 solid 2px'
	else if (pairElementId.value === element.value.id) return '#70b6f080 solid 2px'
	else return 'none'
})

const elementStyle = computed(() => ({
	position: activeElementIds.value.includes(element.value.id) ? 'absolute' : 'fixed',
	width: `${element.value.width}px` || 'auto',
	height: 'auto',
	left: `${element.value.left}px`,
	top: `${element.value.top}px`,
	outline: outline.value,
	boxSizing: 'border-box',
	cursor: isDragging.value ? 'move' : 'default',
}))

const getDynamicComponent = (type) => {
	switch (type) {
		case 'image':
			return ImageElement
		case 'video':
			return VideoElement
		default:
			return TextElement
	}
}

const focusOnElement = (e) => {
	e.stopPropagation()

	// avoid re-triggering focus and putting the cursor at end if text element is already in focus
	if (focusElementId.value == element.value.id) return

	setActiveElements([element.value.id], true)
	nextTick(() => {
		e.target.focus()
	})
}

const selectElement = (e) => {
	if (inSlideShow.value) return

	e.stopPropagation()

	// if the text element is in focus, don't select it again
	if (focusElementId.value == element.value.id) return

	// if the element is already selected and is editable, focus on it
	if (element.value.type == 'text' && element.value.id == activeElement.value?.id)
		focusOnElement(e)
	else setActiveElements([element.value.id])
}

const slideElementRef = useTemplateRef('slideElement')

const currentDragElementRef = inject('currentDragElementRef', null)
const currentDragElement = inject('currentDragElement', null)
const dragOffsets = inject('dragOffsets')

const { isDragging, movement, startDragging, recentSnap } = useDragAndDrop(dragOffsets)

let mousedownStart = 0
let mousedownTimer = null

const handleMouseDown = (event) => {
	mousedownStart = new Date().getTime()
	mousedownTimer = setTimeout(() => {
		currentDragElementRef.value = slideElementRef.value
		currentDragElement.value = element.value
		startDragging(event)
		handleSelect(event)
	}, 200)
}

const handleMouseLeave = () => {
	mousedownStart = 0
	clearTimeout(mousedownTimer)
}

const handleMouseUp = (e) => {
	if (currentDragElementRef.value) {
		currentDragElementRef.value = null
		currentDragElement.value = null
	}
	if (new Date().getTime() < mousedownStart + 200) {
		handleSelect(e)
		clearTimeout(mousedownTimer)
	} else {
		mousedownStart = 0
	}
}

const handleSelect = (e) => {
	if (inSlideShow.value) return

	activeElementIds.value = [element.value.id]
}

watch(
	() => movement.value,
	(movement) => {
		if (!movement) return
		element.value.left += movement.x
		element.value.top += movement.y
	},
)

defineExpose({
	recentSnap,
})
</script>

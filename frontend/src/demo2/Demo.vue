<template>
	<div class="bg-gray-100 w-full h-full fixed flex items-center justify-center">
		<div ref="slide" class="bg-black w-[960px] h-[540px] shadow-2xl">
			<Guides :visibilityMap="visibilityMap" />

			<div
				class="relative bg-blue-400 bg-opacity-30 border border-blue-400 w-[100px] h-[100px]"
				:style="elementStyle"
				@mousedown="(e) => handleMouseDown(e)"
			></div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef } from 'vue'
import Guides from '@/demo2/Guides.vue'

import { useDragAndDrop } from '@/demo2/drag'
import { useSnap } from '@/demo2/snap'

const slideRef = useTemplateRef('slide')
const dragTargetRef = ref(null)

const { startDragging, dragMovement, isDragging } = useDragAndDrop()
const { calculateCenterDiffs, visibilityMap } = useSnap(dragTargetRef, slideRef)

const left = ref(0)
const top = ref(0)

const elementStyle = computed(() => {
	return {
		left: `${left.value}px`,
		top: `${top.value}px`,
		cursor: isDragging.value ? 'move' : 'default',
	}
})

const handleMouseDown = (event) => {
	dragTargetRef.value = event.target
	startDragging(event)
}

const moveElement = (movement) => {
	left.value += movement.x
	top.value += movement.y
}

watch(
	() => dragMovement.value,
	(movement) => {
		calculateCenterDiffs()

		moveElement(movement)
	},
)
</script>

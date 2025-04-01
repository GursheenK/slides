<template>
	<div class="bg-gray-100 w-full h-full fixed flex items-center justify-center">
		<div
			ref="slide"
			class="bg-black w-[960px] h-[540px] shadow-2xl"
			:style="`transform: scale(${scale})`"
		>
			<Guides :visibilityMap="visibilityMap" />

			<div
				class="relative bg-blue-400 bg-opacity-30 border border-blue-400 w-[100px] h-[100px]"
				:style="elementStyle"
				@mousedown="handleMouseDown"
			></div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef } from 'vue'
import Guides from '@/demo/Guides.vue'

import { useDragAndDrop } from '@/utils/drag'
import { useSnapping } from '@/demo/snapping'

const slideRef = useTemplateRef('slide')
const dragTargetRef = ref(null)

const { isDragging, dragMovement, startDragging } = useDragAndDrop()

const { isMovementRestricted, getSnapMovement, calculateCenterDiffs, visibilityMap } = useSnapping(
	dragTargetRef,
	slideRef,
)

const scale = ref(1)
const left = ref(0)
const top = ref(0)

const elementStyle = computed(() => {
	return {
		left: `${left.value}px`,
		top: `${top.value}px`,
	}
})

const handleMouseDown = (event) => {
	dragTargetRef.value = event.target

	startDragging(event)
}

const moveElement = (movement) => {
	left.value += movement.x / scale.value
	top.value += movement.y / scale.value
}

watch(
	() => dragMovement.value,
	(movement) => {
		if (!movement) return

		calculateCenterDiffs()

		let totalMovement = {
			x: 0,
			y: 0,
		}

		if (!isMovementRestricted.value) {
			totalMovement.x += movement.x
			totalMovement.y += movement.y

			const snapMovement = getSnapMovement()

			totalMovement.x += snapMovement.x
			totalMovement.y += snapMovement.y

			moveElement(totalMovement)
		}
	},
)
</script>

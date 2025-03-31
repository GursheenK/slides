<template>
	<div class="bg-gray-200 w-full h-screen flex items-center justify-center fixed">
		<div class="w-[800px] h-[500px] bg-white">
			<div
				ref="element"
				:data-index="'qwerty'"
				class="bg-blue-400 w-20 h-20"
				:style="elementStyle"
				@mousedown="handleMouseDown"
				@mouseup="handleMouseUp"
			></div>
		</div>
	</div>
</template>

<script setup>
import { onMounted, ref, watch, computed } from 'vue'

const activeId = ref([])

const left = ref(0)
const top = ref(0)
const isDragging = ref(false)

const elementStyle = computed(() => {
	return {
		position: 'relative',
		left: `${left.value}px`,
		top: `${top.value}px`,
		cursor: isDragging.value ? 'move' : 'default',
	}
})

let mousedownStart = 0
let mousedownTimer = null

const prevX = ref(0)
const prevY = ref(0)
const movement = ref({
	x: 0,
	y: 0,
})

const handleMouseDown = (event) => {
	mousedownStart = new Date().getTime()
	mousedownTimer = setTimeout(() => {
		handleDragStart(event)
	}, 200)
}

const handleMouseLeave = () => {
	mousedownStart = 0
	clearTimeout(mousedownTimer)
}

const handleMouseUp = (e) => {
	if (new Date().getTime() < mousedownStart + 200) {
		handleSelect(e)
		clearTimeout(mousedownTimer)
	} else {
		mousedownStart = 0
	}
}

const handleSelect = (e) => {
	console.log('handleSelect')
}

const handleDragStart = (event) => {
	console.log('DragStart')
	isDragging.value = true

	prevX.value = event.clientX
	prevY.value = event.clientY
	window.addEventListener('mousemove', handleDrag)
	window.addEventListener('mouseup', handleDragStop)
}

const handleDrag = (event) => {
	console.log('Drag')
	const dx = event.clientX - prevX.value
	const dy = event.clientY - prevY.value

	movement.value = {
		x: dx,
		y: dy,
	}

	prevX.value = event.clientX
	prevY.value = event.clientY
}

const handleDragStop = (event) => {
	console.log('DragStop')
	isDragging.value = false
	window.removeEventListener('mousemove', handleDrag)
	window.removeEventListener('mouseup', handleDragStop)
}

watch(
	() => movement.value,
	(movement) => {
		if (isDragging) {
			left.value = left.value + movement.x
			top.value = top.value + movement.y
		}
	},
)
</script>

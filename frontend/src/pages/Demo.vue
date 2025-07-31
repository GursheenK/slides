<template>
	<div class="flex gap-2">
		<Button label="Change Something" class="m-20" @click="changeSomething" />
		<Button label="Undo" class="m-20" @click="historyControl?.undo" />
	</div>
	<pre class="m-20 h-80 overflow-y-auto border">{{ state }}</pre>
	{{ historyControl?.history }}
</template>

<script setup>
import cloneDeep from 'lodash/cloneDeep'
import { watch, onMounted, ref } from 'vue'
import { useDebouncedRefHistory } from '@vueuse/core'

import { presentation, presentationId } from '@/stores/presentation'

let historyControl

const changeSomething = () => {
	// const currentElements = JSON.parse(state.value[0].elements)
	// currentElements.push({
	// 	type: 'text',
	// 	content: 'New Text Element',
	// 	style: {
	// 		fontSize: '20px',
	// 		color: '#333',
	// 	},
	// })
	// state.value[0].elements = JSON.stringify(currentElements)

	state.value.push({
		name: 'jfhrin2ngm',
		owner: 'Administrator',
		creation: '2025-07-29 20:27:40.978270',
		modified: '2025-07-30 22:41:16.297087',
		modified_by: 'Administrator',
		docstatus: 0,
		idx: 1,
		background: '#ffffff',
		elements: '[]',
		thumbnail: '/assets/slides/frontend/images/layouts/light/thumbnail-1.png',
		parent: 'jb1f70hj4o',
		parentfield: 'slides',
		parenttype: 'Presentation',
		doctype: 'Slide',
	})
}

const state = ref(null)

onMounted(() => {
	presentationId.value = 'jb1f70hj4o'
	presentation.fetch().then((data) => {
		state.value = JSON.parse(JSON.stringify(data.slides))
		historyControl = useDebouncedRefHistory(state, {
			deep: true,
			clone: cloneDeep,
			capacity: 10,
			debounce: 5000,
		})
	})
})
</script>

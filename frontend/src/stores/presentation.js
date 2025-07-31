import { ref, watch } from 'vue'
import { useDebouncedRefHistory } from '@vueuse/core'
import { cloneDeep } from 'lodash/cloneDeep'
import { createResource, call } from 'frappe-ui'

const presentationId = ref('')
const state = ref([])

let historyControl = null

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: presentationId.value }),
	onSuccess: (data) => {
		const slidesCopy = JSON.parse(JSON.stringify(data.slides))
		state.value = slidesCopy.map((slide) => ({
			...slide,
			elements: JSON.parse(slide.elements || '[]'),
		}))
	},
})

watch(
	() => presentation.fetched,
	(fetched) => {
		historyControl = useDebouncedRefHistory(state, {
			deep: true,
			clone: cloneDeep,
			capacity: 10,
			debounce: 5000,
		})
	},
)

const inSlideShow = ref(false)

const applyReverseTransition = ref(false)

const createPresentationResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.create_presentation',
	method: 'POST',
	makeParams: (args) => {
		return {
			title: args.title,
			duplicate_from: args.duplicateFrom,
		}
	},
})

const updatePresentationTitle = async (id, newTitle) => {
	return call('slides.slides.doctype.presentation.presentation.update_title', {
		name: id,
		title: newTitle,
	}).then((response) => {
		if (response) {
			return response
		} else {
			throw new Error('Failed to rename presentation')
		}
	})
}

export {
	presentationId,
	presentation,
	inSlideShow,
	applyReverseTransition,
	createPresentationResource,
	updatePresentationTitle,
	state,
	historyControl,
}

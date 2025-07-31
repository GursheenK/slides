<template>
	<div :class="sectionClasses">
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between">
				<div :class="sectionTitleClasses">Slide</div>
				<div class="pe-0.5 text-2xs font-semibold text-gray-700">
					{{ slideIndex + 1 + ' of ' + state.length }}
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Background Color</div>
				<ColorPicker v-model="state[slideIndex].background" />
			</div>
		</div>
	</div>

	<CollapsibleSection title="Transition" :initialState="true">
		<template #default>
			<Select
				:options="['Slide In', 'Fade', 'None']"
				:modelValue="state[slideIndex].transition || 'None'"
				@update:modelValue="(option) => setSlideTransition(option)"
			/>

			<SliderInput
				v-show="state[slideIndex].transition && state[slideIndex].transition != 'None'"
				label="Duration"
				:rangeStart="0"
				:rangeEnd="4"
				:rangeStep="0.1"
				:modelValue="parseFloat(state[slideIndex].transitionDuration)"
				@update:modelValue="(value) => setTransitionDuration(value)"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { Select } from 'frappe-ui'

import { state, presentation } from '@/stores/presentation'
import { slideIndex } from '@/stores/slide'
import { sectionClasses, sectionTitleClasses, fieldLabelClasses } from '@/utils/constants'

import SliderInput from '@/components/controls/SliderInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

const setSlideTransition = (option) => {
	state.value[slideIndex.value].transition = option
	if (option.value == 'None') state.value[slideIndex.value].transitionDuration = 0
	else state.value[slideIndex.value].transitionDuration = 1
}

const setTransitionDuration = (value) => {
	state.value[slideIndex.value].transitionDuration = value
}
</script>

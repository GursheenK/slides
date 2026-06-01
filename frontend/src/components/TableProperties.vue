<template>
	<CollapsibleSection title="Table">
		<template #default>
			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Rows</div>
				<div class="w-28">
					<NumberInput
						:modelValue="activeElement.rows"
						@update:modelValue="handleRowsChange"
						:rangeStart="1"
						:rangeEnd="20"
						:rangeStep="1"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Cols</div>
				<div class="w-28">
					<NumberInput
						:modelValue="activeElement.cols"
						@update:modelValue="handleColsChange"
						:rangeStart="1"
						:rangeEnd="20"
						:rangeStep="1"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Header</div>
				<div class="w-28">
					<FormControl
						type="select"
						:options="headerOptions"
						:modelValue="activeElement.header"
						@update:modelValue="handleHeaderChange"
					/>
				</div>
			</div>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { inject, nextTick } from 'vue'
import { FormControl } from 'frappe-ui'

import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'
import NumberInput from '@/components/controls/NumberInput.vue'

import { activeElement, activeTableEditor } from '@/stores/element'
import { currentSlide } from '@/stores/slide'
import { commandHistory } from '@/stores/historyMeta'
import { editElementCommand, batchCommand } from '@/stores/commands'
import { fieldLabelClasses } from '@/utils/constants'

const setProperty = inject('setProperty')

const headerOptions = [
	{ label: 'None', value: 'none' },
	{ label: 'Row', value: 'row' },
	{ label: 'Col', value: 'col' },
	{ label: 'Both', value: 'both' },
]

const syncStructuralChange = (command, rowsDelta, colsDelta, repeat = 1) => {
	const editor = activeTableEditor.value
	if (!editor) return
	const oldContent = editor.getHTML()
	const oldRows = activeElement.value.rows
	const oldCols = activeElement.value.cols

	let chain = editor.chain().focus()
	for (let i = 0; i < repeat; i++) chain = chain[command]()
	chain.run()

	nextTick(() => {
		const commands = [
			editElementCommand({
				slideId: currentSlide.value.clientId,
				elementIds: [activeElement.value.id],
				property: 'content',
				oldValue: oldContent,
				newValue: editor.getHTML(),
			}),
		]
		if (rowsDelta !== 0) {
			commands.push(
				editElementCommand({
					slideId: currentSlide.value.clientId,
					elementIds: [activeElement.value.id],
					property: 'rows',
					oldValue: oldRows,
					newValue: oldRows + rowsDelta,
				}),
			)
		}
		if (colsDelta !== 0) {
			commands.push(
				editElementCommand({
					slideId: currentSlide.value.clientId,
					elementIds: [activeElement.value.id],
					property: 'cols',
					oldValue: oldCols,
					newValue: oldCols + colsDelta,
				}),
			)
		}
		commandHistory.execute(
			batchCommand({
				slideId: currentSlide.value.clientId,
				elementIds: [activeElement.value.id],
				commands,
			}),
		)
	})
}

const handleRowsChange = (newVal) => {
	const delta = newVal - activeElement.value.rows
	if (delta === 0) return
	syncStructuralChange(delta > 0 ? 'addRowAfter' : 'deleteRow', delta, 0, Math.abs(delta))
}

const handleColsChange = (newVal) => {
	const delta = newVal - activeElement.value.cols
	if (delta === 0) return
	syncStructuralChange(delta > 0 ? 'addColumnAfter' : 'deleteColumn', 0, delta, Math.abs(delta))
}

const handleHeaderChange = (newVal) => {
	const editor = activeTableEditor.value
	const oldVal = activeElement.value.header
	if (newVal === oldVal) return

	if (!editor) {
		setProperty('header', newVal)
		return
	}

	const needsHeaderRow = newVal === 'row' || newVal === 'both'
	const hasHeaderRow = oldVal === 'row' || oldVal === 'both'
	const needsHeaderCol = newVal === 'col' || newVal === 'both'
	const hasHeaderCol = oldVal === 'col' || oldVal === 'both'

	const oldContent = editor.getHTML()
	let chain = editor.chain().focus()
	if (needsHeaderRow !== hasHeaderRow) chain = chain.toggleHeaderRow()
	if (needsHeaderCol !== hasHeaderCol) chain = chain.toggleHeaderColumn()
	chain.run()

	nextTick(() => {
		commandHistory.execute(
			batchCommand({
				slideId: currentSlide.value.clientId,
				elementIds: [activeElement.value.id],
				commands: [
					editElementCommand({
						slideId: currentSlide.value.clientId,
						elementIds: [activeElement.value.id],
						property: 'content',
						oldValue: oldContent,
						newValue: editor.getHTML(),
					}),
					editElementCommand({
						slideId: currentSlide.value.clientId,
						elementIds: [activeElement.value.id],
						property: 'header',
						oldValue: oldVal,
						newValue: newVal,
					}),
				],
			}),
		)
	})
}
</script>

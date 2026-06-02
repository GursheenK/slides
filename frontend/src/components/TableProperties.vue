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

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Border Width</div>
				<div class="w-28">
					<NumberInput
						:modelValue="activeElement.borderWidth"
						@update:modelValue="setProperty('borderWidth', $event)"
						:rangeStart="0"
						:rangeEnd="10"
						:rangeStep="1"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Border Color</div>
				<ColorPicker
					v-model="activeElement.borderColor"
					@colordown="onBorderColorUpdateStart"
					@colorup="onBorderColorUpdateEnd"
				/>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Header Color</div>
				<ColorPicker
					v-model="activeElement.headerColor"
					@colordown="onHeaderColorUpdateStart"
					@colorup="onHeaderColorUpdateEnd"
				/>
			</div>
		</template>
	</CollapsibleSection>

	<CollapsibleSection v-if="showCellSection" title="Cell">
		<div class="flex items-center justify-between" @mousedown.prevent>
			<div :class="fieldLabelClasses">Fill</div>
			<Checkbox
				size="sm"
				class="cursor-pointer px-1"
				:modelValue="tableEditorStyles.backgroundColor !== null"
				@update:modelValue="setCellFillEnabled"
			/>
		</div>

		<div
			v-if="tableEditorStyles.backgroundColor !== null"
			class="flex items-center justify-between"
			@mousedown.prevent
		>
			<div :class="fieldLabelClasses">Fill Color</div>
			<ColorPicker
				:modelValue="tableEditorStyles.backgroundColor"
				@update:modelValue="setCellBackground($event)"
			/>
		</div>
	</CollapsibleSection>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'
import { FormControl, Checkbox } from 'frappe-ui'

import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'

import {
	activeElement,
	activeTableEditor,
	tableEditorStyles,
	focusElementId,
} from '@/stores/element'
import { currentSlide } from '@/stores/slide'
import { commandHistory } from '@/stores/historyMeta'
import { editElementCommand, batchCommand } from '@/stores/commands'
import { fieldLabelClasses } from '@/utils/constants'

const cellWasFocused = ref(false)

watch(
	() => focusElementId.value,
	(val) => {
		if (val === activeElement.value?.id) cellWasFocused.value = true
	},
)

watch(activeTableEditor, (editor) => {
	if (!editor) cellWasFocused.value = false
})

const showCellSection = computed(() => cellWasFocused.value && activeTableEditor.value !== null)

const setCellBackground = (val) => {
	const editor = activeTableEditor.value
	if (!editor) return
	editor.chain().setCellAttribute('backgroundColor', val).run()
}

const setCellFillEnabled = (enabled) => {
	setCellBackground(enabled ? '#FFFFFFFF' : null)
}

const setProperty = inject('setProperty')
const setPropertyDeferred = inject('setPropertyDeferred')

const { onStart: onBorderColorUpdateStart, onEnd: onBorderColorUpdateEnd } = setPropertyDeferred(
	'element',
	'borderColor',
)

const { onStart: onHeaderColorUpdateStart, onEnd: onHeaderColorUpdateEnd } = setPropertyDeferred(
	'element',
	'headerColor',
)

const headerOptions = [
	{ label: 'None', value: 'none' },
	{ label: 'Row', value: 'row' },
	{ label: 'Col', value: 'col' },
	{ label: 'Both', value: 'both' },
]

const getTableRows = (editor) => {
	const rows = []
	editor.state.doc.descendants((node, pos) => {
		if (node.type.name === 'tableRow') rows.push({ node, pos })
	})
	return rows
}

// Position of the last cell in the first row — used to anchor column commands
const getLastCellPos = (editor) => {
	const firstRow = getTableRows(editor)[0]
	let lastOffset = 0
	firstRow.node.forEach((_, offset) => {
		lastOffset = offset
	})
	return firstRow.pos + 1 + lastOffset + 1
}

// --- Row/col mutation helpers (return actual count changed) ---

const addRowsAfterLast = (editor, count) => {
	const lastRow = getTableRows(editor).at(-1)
	let chain = editor
		.chain()
		.focus()
		.setTextSelection(lastRow.pos + 2)
	for (let i = 0; i < count; i++) chain = chain.addRowAfter()
	chain.run()
	return count
}

// Deletes up to `max` empty rows from the end; stops at first row with content
const deleteEmptyRowsFromEnd = (editor, max) => {
	const rows = getTableRows(editor)
	let count = 0
	for (let i = rows.length - 1; i >= 0 && count < max; i--) {
		if (rows[i].node.textContent.trim() !== '') break
		count++
	}
	if (count === 0) return 0
	// Single transaction, end → start so positions stay valid
	const toRemove = rows.slice(rows.length - count)
	let tr = editor.state.tr
	for (let i = toRemove.length - 1; i >= 0; i--) {
		tr = tr.delete(toRemove[i].pos, toRemove[i].pos + toRemove[i].node.nodeSize)
	}
	editor.view.dispatch(tr)
	return count
}

const addColsAfterLast = (editor, count) => {
	let chain = editor.chain().focus().setTextSelection(getLastCellPos(editor))
	for (let i = 0; i < count; i++) chain = chain.addColumnAfter()
	chain.run()
	return count
}

// Deletes up to `max` empty columns from the end; stops at first col with content
const deleteEmptyColsFromEnd = (editor, max) => {
	let count = 0
	for (let i = 0; i < max; i++) {
		const rows = getTableRows(editor)
		const lastColHasContent = rows.some(({ node }) => node.lastChild?.textContent.trim() !== '')
		if (lastColHasContent) break
		editor.chain().focus().setTextSelection(getLastCellPos(editor)).deleteColumn().run()
		count++
	}
	return count
}

const commitDelta = (editor, oldContent, rowsDelta, colsDelta) => {
	const { rows, cols, id } = activeElement.value
	const slideId = currentSlide.value.clientId
	const el = { slideId, elementIds: [id] }

	const commands = [
		editElementCommand({
			...el,
			property: 'content',
			oldValue: oldContent,
			newValue: editor.getHTML(),
		}),
	]
	if (rowsDelta !== 0)
		commands.push(
			editElementCommand({
				...el,
				property: 'rows',
				oldValue: rows,
				newValue: rows + rowsDelta,
			}),
		)
	if (colsDelta !== 0)
		commands.push(
			editElementCommand({
				...el,
				property: 'cols',
				oldValue: cols,
				newValue: cols + colsDelta,
			}),
		)

	commandHistory.execute(batchCommand({ ...el, commands }))
}

const handleRowsChange = (newVal) => {
	const editor = activeTableEditor.value
	if (!editor) return
	const expectedDelta = newVal - activeElement.value.rows
	if (expectedDelta === 0) return

	const oldContent = editor.getHTML()
	let actualDelta
	if (expectedDelta > 0) actualDelta = addRowsAfterLast(editor, expectedDelta)
	else actualDelta = -deleteEmptyRowsFromEnd(editor, -expectedDelta)
	if (actualDelta === 0) return
	commitDelta(editor, oldContent, actualDelta, 0)
}

const handleColsChange = (newVal) => {
	const editor = activeTableEditor.value
	if (!editor) return
	const expectedDelta = newVal - activeElement.value.cols
	if (expectedDelta === 0) return

	const oldContent = editor.getHTML()
	let actualDelta
	if (expectedDelta > 0) actualDelta = addColsAfterLast(editor, expectedDelta)
	else actualDelta = -deleteEmptyColsFromEnd(editor, -expectedDelta)
	if (actualDelta === 0) return
	commitDelta(editor, oldContent, 0, actualDelta)
}

const handleHeaderChange = (newVal) => {
	const editor = activeTableEditor.value
	const oldVal = activeElement.value.header
	if (newVal === oldVal) return

	if (!editor) return

	const needsHeaderRow = newVal === 'row' || newVal === 'both'
	const hasHeaderRow = oldVal === 'row' || oldVal === 'both'
	const needsHeaderCol = newVal === 'col' || newVal === 'both'
	const hasHeaderCol = oldVal === 'col' || oldVal === 'both'

	const oldContent = editor.getHTML()
	let chain = editor.chain().focus()
	if (needsHeaderRow !== hasHeaderRow) chain = chain.toggleHeaderRow()
	if (needsHeaderCol !== hasHeaderCol) chain = chain.toggleHeaderColumn()
	chain.run()

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
}
</script>

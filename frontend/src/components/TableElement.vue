<template>
	<div
		class="table-element h-full w-full"
		:style="{ '--cell-border': cellBorder }"
		@mousedown="handleMouseDown"
	>
		<EditorContent v-if="showEditor" :editor="editor" class="h-full w-full" />
		<div v-else v-html="element.content" class="h-full w-full select-none" />
	</div>
</template>

<script setup>
import { computed, watchEffect, shallowRef } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'

import { tableExtensions } from '@/stores/tiptapSetup'
import { activeElement } from '@/stores/element'
import { currentSlide } from '@/stores/slide'
import { commandHistory } from '@/stores/historyMeta'
import { editElementCommand } from '@/stores/commands'

const props = defineProps({
	mode: { type: String, default: 'editor' },
	elementOffset: { type: Object, default: () => ({ left: 0, top: 0 }) },
	transitionStyles: { type: Object, default: () => ({}) },
})

const element = defineModel('element', { type: Object, default: null })
const emit = defineEmits(['clearTimeouts'])

const showEditor = computed(
	() => activeElement.value?.id === element.value.id && props.mode === 'editor',
)

const editor = shallowRef(null)
let contentSnapshot = null

watchEffect((onCleanup) => {
	if (!showEditor.value) return

	const instance = new Editor({
		content: element.value.content,
		extensions: tableExtensions,
		editable: true,
		editorProps: { attributes: { class: 'outline-none h-full w-full' } },
	})

	instance.on('focus', () => {
		contentSnapshot = instance.getHTML()
	})
	instance.on('blur', () => {
		const newContent = instance.getHTML()
		if (contentSnapshot !== null && newContent !== contentSnapshot) {
			commandHistory.execute(
				editElementCommand({
					slideId: currentSlide.value.clientId,
					elementIds: [element.value.id],
					property: 'content',
					oldValue: contentSnapshot,
					newValue: newContent,
				}),
			)
		}
		contentSnapshot = null
	})

	editor.value = instance

	onCleanup(() => {
		instance.destroy()
		editor.value = null
		contentSnapshot = null
	})
})

const cellBorder = computed(
	() => `${element.value.borderWidth}px solid ${element.value.borderColor}`,
)

const handleMouseDown = (e) => {
	if (editor.value?.view.dom.classList.contains('resize-cursor')) {
		// needed to not drag table when col resizing
		e.stopPropagation()
	}
}
</script>

<style>
.table-element table {
	border-collapse: collapse;
	width: 100%;
}
.table-element td,
.table-element th {
	border: var(--cell-border);
	/* min width is needed because col resizing shouldn't collapse two columns into same boundary */
	min-width: 1px;
	vertical-align: top;
}
</style>

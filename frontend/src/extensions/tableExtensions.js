import { Table, TableRow, TableCell, TableHeader } from '@tiptap/extension-table'

const CustomTableCell = TableCell.extend({
	addAttributes() {
		return {
			...this.parent?.(),
			backgroundColor: {
				default: null,
				parseHTML: (el) => el.style.backgroundColor || null,
				renderHTML: (attrs) =>
					attrs.backgroundColor
						? { style: `background-color: ${attrs.backgroundColor}` }
						: {},
			},
		}
	},
	renderHTML({ HTMLAttributes }) {
		return ['td', HTMLAttributes, ['div', { class: 'cell-content' }, 0]]
	},
})

const CustomTableHeader = TableHeader.extend({
	addAttributes() {
		return {
			...this.parent?.(),
			backgroundColor: {
				default: null,
				parseHTML: (el) => el.style.backgroundColor || null,
				renderHTML: (attrs) =>
					attrs.backgroundColor
						? { style: `background-color: ${attrs.backgroundColor}` }
						: {},
			},
		}
	},
	renderHTML({ HTMLAttributes }) {
		return ['th', HTMLAttributes, ['div', { class: 'cell-content' }, 0]]
	},
})

export const tableNodes = [
	Table.configure({ resizable: true, lastColumnResizable: false }),
	TableRow,
	CustomTableCell,
	CustomTableHeader,
]

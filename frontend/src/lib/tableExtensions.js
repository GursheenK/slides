import { TableCell, TableHeader } from '@tiptap/extension-table'

export const CustomTableCell = TableCell.extend({
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
})

export const CustomTableHeader = TableHeader.extend({
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
})

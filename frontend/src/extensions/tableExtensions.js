import { Table, TableRow, TableCell, TableHeader } from '@tiptap/extension-table'

export const tableNodes = [Table.configure({ resizable: true }), TableRow, TableCell, TableHeader]

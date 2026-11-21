// Màu dùng trong SVG/Recharts (thuộc tính stroke/fill cần giá trị cụ thể). PHẢI khớp @theme trong styles/global.css.
export const COLORS = {
  merino: '#f1f1ec',
  kangaroo: '#d0c7b3',
  oyster: '#939474',
  oysterInk: '#6f7052',
  rifle: '#43442b',
  cedar: '#29272b',
  rust: '#a3442a',
  brass: '#9c7a3c',
} as const

/** Màu theo loại khách sạn: City = Rifle, Resort = Brass (như prototype). */
export function hotelColor(hotelType: string | undefined | null): string {
  return hotelType === 'Resort' ? COLORS.brass : COLORS.rifle
}

export const FONT_MONO = "'IBM Plex Mono', ui-monospace, Menlo, Consolas, monospace"
export const FONT_UI = "'Hanken Grotesk', ui-sans-serif, system-ui, sans-serif"

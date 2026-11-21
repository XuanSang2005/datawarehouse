# frontend/: React + Vite + TypeScript + Tailwind CSS

Giao diện cho người ra quyết định, theo prototype `docs/design/prototype/` ("Maré Revenue Desk").
Mọi request `/api/*` được Vite proxy sang backend (cổng `BACKEND_PORT` trong `.env` ở thư mục gốc).

```
src/
├── main.tsx             Điểm khởi động (Router + FiltersProvider)
├── App.tsx              Router + layout
├── routes.tsx           ★ Danh sách trang (thanh điều hướng tự sinh từ đây)
├── pages/               Mỗi trang = 1 file *Page.tsx
├── components/
│   ├── layout/          Khung trang: thanh trên (logo, menu, chọn khách sạn), footer
│   ├── common/          ledger.tsx (Section, Focal, KpiStrip, Tabs, BarCell...), DataState, ErrorBox
│   ├── charts/          LedgerLineChart (Recharts), ColumnBars
│   └── filters/         FilterBar (ngày đến, kênh, quốc gia)
├── context/             Bộ lọc dùng chung cho mọi trang
├── api/
│   ├── client.ts        fetch dùng chung + chuẩn hóa lỗi (ApiError, có hint từ backend)
│   └── endpoints.ts     ★ Mỗi endpoint backend = 1 hàm
├── hooks/               useApi (data / error / loading, gọi lại khi deps đổi), useDebounced, useToast
├── lib/                 format.ts (số kiểu vi-VN, EUR), theme.ts (màu hex cho SVG)
├── types/api.ts         ★ Kiểu dữ liệu, PHẢI khớp backend/app/schemas
└── styles/global.css    Tailwind + token thiết kế (@theme)
```

## Chạy
```bash
npm install
```
```bash
npm run dev
```
Mở http://localhost:5173 (cần backend đang chạy ở cổng 8000).

## Kiểm tra trước khi push
```bash
npm run lint && npm run build
```

## Thêm trang
`types/api.ts` → `api/endpoints.ts` → `pages/XxxPage.tsx` → thêm 1 dòng vào `routes.tsx`.

## Quy ước giao diện
- Style bằng utility class Tailwind trong TSX. Màu dùng token: `bg-rifle`, `text-oyster-ink`, `border-kangaroo`...
  (khai báo ở `styles/global.css`). Không thêm file CSS riêng cho từng trang.
- `rust` (đỏ gạch) **chỉ** dùng cho hủy phòng / giá trị âm; `rifle` cho City Hotel, `brass` cho Resort Hotel.
- Mỗi trang có đúng một khối `<Focal>` (nền xanh Rifle) làm điểm nhấn; các phần ngăn bằng `<Section>` (đường kẻ trên).
- Không tính KPI ở frontend: tỉ lệ/ADR/what-if lấy từ backend, frontend chỉ định dạng bằng `lib/format.ts`.
- Mọi khối dữ liệu bọc trong `<DataState>` để có trạng thái tải / lỗi / rỗng thống nhất.

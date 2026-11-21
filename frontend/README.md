# frontend/: React + Vite + TypeScript

Giao diện cho người ra quyết định. Mọi request `/api/*` được Vite proxy sang backend (cổng `BACKEND_PORT` trong `.env` ở thư mục gốc).

```
src/
├── main.tsx             Điểm khởi động
├── App.tsx              Router + layout
├── routes.tsx           ★ Danh sách trang (sidebar tự sinh từ đây)
├── pages/               Mỗi trang = 1 file *Page.tsx
├── components/
│   ├── layout/          Khung trang, sidebar
│   └── common/          Badge, ErrorBox, ... (thêm charts/, filters/ khi cần)
├── api/
│   ├── client.ts        fetch dùng chung + chuẩn hóa lỗi (ApiError)
│   └── endpoints.ts     ★ Mỗi endpoint backend = 1 hàm
├── hooks/useApi.ts      Gọi API: data / error / loading / reload
├── types/api.ts         ★ Kiểu dữ liệu, PHẢI khớp backend/app/schemas
└── styles/global.css
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

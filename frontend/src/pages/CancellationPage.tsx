import PlannedPage from '../components/common/PlannedPage'

export default function CancellationPage() {
  return (
    <PlannedPage
      title="Rủi ro hủy phòng"
      decisionMaker="Revenue Manager, bộ phận Reservations"
      decisions={['Booking nào cần gọi xác nhận / yêu cầu đặt cọc?', 'Phân khúc nào hủy nhiều nhất?']}
      features={[
        'Phân tích tỉ lệ hủy theo lead time, kênh, loại đặt cọc, quốc gia',
        'Danh sách booking có xác suất hủy cao (từ mô hình ML)',
        'Chỉ số đánh giá mô hình (AUC, precision, recall)',
      ]}
    />
  )
}

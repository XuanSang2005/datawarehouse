import PlannedPage from '../components/common/PlannedPage'

export default function ForecastPage() {
  return (
    <PlannedPage
      title="Dự báo nhu cầu"
      decisionMaker="Revenue Manager, Sales & Marketing Manager"
      decisions={['Chuẩn bị nhân sự, giá phòng cho các tuần sắp tới', 'Chọn thời điểm chạy khuyến mãi']}
      features={['Dự báo room-nights theo tuần cho từng khách sạn', 'So sánh dự báo và thực tế (MAPE)']}
    />
  )
}

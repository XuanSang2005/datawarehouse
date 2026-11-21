import PlannedPage from '../components/common/PlannedPage'

export default function OverviewPage() {
  return (
    <PlannedPage
      title="Tổng quan KPI"
      decisionMaker="General Manager"
      decisions={['So sánh hiệu quả City Hotel và Resort Hotel', 'Theo dõi xu hướng doanh thu theo mùa']}
      features={[
        'KPI: doanh thu, room-nights, ADR, tỉ lệ hủy, lead time',
        'Bộ lọc khách sạn / thời gian / kênh / quốc gia (slice & dice)',
        'Drill-down Năm → Quý → Tháng → Tuần',
      ]}
    />
  )
}

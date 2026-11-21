import PlannedPage from '../components/common/PlannedPage'

export default function WhatIfPage() {
  return (
    <PlannedPage
      title="Mô phỏng What-if"
      decisionMaker="Revenue Manager"
      decisions={['Overbook bao nhiêu % là an toàn?', 'Áp đặt cọc cho nhóm booking rủi ro cao có lợi không?']}
      features={[
        'Thanh trượt mức overbooking, công suất phòng, chính sách đặt cọc',
        'Ước tính doanh thu cứu được và rủi ro hết phòng',
      ]}
    />
  )
}

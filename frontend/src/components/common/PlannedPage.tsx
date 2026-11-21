// Khung tạm cho các trang chưa làm: ghi rõ ai dùng & quyết định gì để nhóm bám sát bài toán.
interface Props {
  title: string
  decisionMaker: string
  decisions: string[]
  features: string[]
}

export default function PlannedPage({ title, decisionMaker, decisions, features }: Props) {
  return (
    <section>
      <h1>{title}</h1>
      <p className="muted">Trang đang được xây dựng.</p>
      <div className="card">
        <h3>Người dùng: {decisionMaker}</h3>
        <h4>Quyết định cần hỗ trợ</h4>
        <ul>{decisions.map((d) => <li key={d}>{d}</li>)}</ul>
        <h4>Tính năng dự kiến</h4>
        <ul>{features.map((f) => <li key={f}>{f}</li>)}</ul>
      </div>
    </section>
  )
}

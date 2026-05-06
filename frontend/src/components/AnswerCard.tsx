import './AnswerCard.css';

interface Props {
  answer: string;
  isChitchat: boolean;
}

export default function AnswerCard({ answer, isChitchat }: Props) {
  return (
    <section className={`answer-card card fade-in ${isChitchat ? 'answer-card--chitchat' : ''}`}>
      <div className="card-header">{isChitchat ? '回答' : 'AI 解读'}</div>
      <p className="answer-card-text">{answer}</p>
    </section>
  );
}

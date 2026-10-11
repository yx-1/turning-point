import type { Reading } from "../types/chat";

interface ReadingViewProps {
  reading: Reading;
  onStartOver: () => void;
}

export function ReadingView({ reading, onStartOver }: ReadingViewProps) {
  return (
    <article className="reading">
      <p className="reading-kicker">Local chart reading</p>
      <h2>Your reading</h2>
      <p className="reading-natal">{reading.natal_summary}</p>
      {reading.time_note ? <p className="reading-note">{reading.time_note}</p> : null}

      <section>
        <h3>Your Past Pattern</h3>
        <p>{reading.past_pattern}</p>
      </section>
      <section>
        <h3>Future Transition Window</h3>
        <p className="reading-window">{reading.future_window}</p>
      </section>
      <section>
        <h3>Possible Themes</h3>
        <ul>
          {reading.themes.map((theme) => (
            <li key={theme}>{theme}</li>
          ))}
        </ul>
      </section>
      <section>
        <h3>Why This Period Stands Out</h3>
        <p>{reading.why}</p>
      </section>
      <section>
        <h3>Similarities to Past Events</h3>
        <p>{reading.similarities}</p>
      </section>
      <section>
        <h3>How to Prepare</h3>
        <p>{reading.preparation}</p>
      </section>
      <section>
        <h3>Disclaimer</h3>
        <p>{reading.disclaimer}</p>
      </section>

      <button type="button" className="send-button start-over" onClick={onStartOver}>
        Start Over
      </button>
    </article>
  );
}

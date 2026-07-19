import type { RetrievalSource } from "../lib/retrieval-api";
import { Icon } from "./ui/icons";
import styles from "./chat-retrieval-sources.module.css";

export function RetrievalSourceList({ sources }: { sources: RetrievalSource[] }) {
  if (sources.length === 0) return null;

  return (
    <details className={styles.sources}>
      <summary>
        <Icon className={styles.icon} name="memory" size={12} />
        <span>
          {sources.length} {sources.length === 1 ? "source" : "sources"}
        </span>
        <small>{sources.map((source) => `[${source.label}]`).join(" ")}</small>
        <Icon className={styles.chevron} name="chevron-right" size={12} />
      </summary>
      <div className={styles.list}>
        {sources.map((source) => (
          <article className={styles.source} key={source.id}>
            <header>
              <strong>[{source.label}]</strong>
              <span>{source.kind === "memory" ? "Approved memory" : "Private document"}</span>
              {source.score !== null && <small>{source.score.toFixed(3)}</small>}
            </header>
            <p>{source.content}</p>
          </article>
        ))}
      </div>
    </details>
  );
}

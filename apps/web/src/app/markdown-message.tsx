"use client";

import { Children, isValidElement, useEffect, useMemo, useState, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

import { Icon } from "./ui/icons";

export async function copyText(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("The browser could not copy this content.");
}

export function normalizeStreamingMarkdown(content: string): string {
  let normalized = content;
  const backtickFences = content.match(/(^|\n)```/g)?.length ?? 0;
  const tildeFences = content.match(/(^|\n)~~~/g)?.length ?? 0;

  if (backtickFences % 2 === 1) normalized += "\n```";
  if (tildeFences % 2 === 1) normalized += "\n~~~";
  return normalized;
}

type SplitMessageContent = {
  answer: string;
  reasoning: string | null;
  reasoningStreaming: boolean;
};

function splitReasoningContent(content: string, streaming: boolean): SplitMessageContent {
  const answerParts: string[] = [];
  const reasoningParts: string[] = [];
  let cursor = 0;
  let reasoningStreaming = false;

  while (cursor < content.length) {
    const remaining = content.slice(cursor);
    const opening = /<(think|analysis|reasoning)>/i.exec(remaining);
    if (!opening) break;

    const openingStart = cursor + opening.index;
    const bodyStart = openingStart + opening[0].length;
    answerParts.push(content.slice(cursor, openingStart));

    const tagName = opening[1];
    const closing = new RegExp(`</${tagName}>`, "i").exec(content.slice(bodyStart));
    if (!closing) {
      if (streaming) {
        reasoningParts.push(content.slice(bodyStart));
        reasoningStreaming = true;
      } else {
        answerParts.push(content.slice(openingStart));
      }
      cursor = content.length;
      break;
    }

    reasoningParts.push(content.slice(bodyStart, bodyStart + closing.index));
    cursor = bodyStart + closing.index + closing[0].length;
  }

  answerParts.push(content.slice(cursor));
  const reasoning = reasoningParts
    .map((part) => part.trim())
    .filter(Boolean)
    .join("\n\n");

  return {
    answer: answerParts.join("").replace(/^\s+/, ""),
    reasoning: reasoning || null,
    reasoningStreaming,
  };
}

function MarkdownBody({
  className = "",
  content,
  streaming,
}: {
  className?: string;
  content: string;
  streaming: boolean;
}) {
  const renderedContent = useMemo(
    () => (streaming ? normalizeStreamingMarkdown(content) : content),
    [content, streaming],
  );

  return (
    <div className={`markdown-content ${streaming ? "streaming" : ""} ${className}`.trim()}>
      <ReactMarkdown
        components={markdownComponents}
        rehypePlugins={[rehypeHighlight]}
        remarkPlugins={[remarkGfm, remarkBreaks]}
        skipHtml
      >
        {renderedContent || (streaming ? "…" : "")}
      </ReactMarkdown>
    </div>
  );
}

export function MarkdownMessage({ content, streaming }: { content: string; streaming: boolean }) {
  const splitContent = useMemo(
    () => splitReasoningContent(content, streaming),
    [content, streaming],
  );

  return (
    <div className="message-rendered-content">
      {splitContent.reasoning ? (
        <details className={`reasoning-disclosure ${splitContent.reasoningStreaming ? "streaming" : ""}`}>
          <summary>
            <Icon className="reasoning-chevron" name="chevron-right" size={13} />
            <span>{splitContent.reasoningStreaming ? "Reasoning…" : "Reasoning"}</span>
            <small>Show details</small>
          </summary>
          <MarkdownBody
            className="reasoning-content"
            content={splitContent.reasoning}
            streaming={splitContent.reasoningStreaming}
          />
        </details>
      ) : null}
      {splitContent.answer ? (
        <MarkdownBody content={splitContent.answer} streaming={streaming} />
      ) : null}
    </div>
  );
}

const markdownComponents: Components = {
  pre: CodeBlock,
  table: ({ children }) => (
    <div className="markdown-table-wrap">
      <table>{children}</table>
    </div>
  ),
};

function CodeBlock({ children }: { children?: ReactNode }) {
  const [copied, setCopied] = useState(false);
  const code = extractText(children).replace(/\n$/, "");
  const firstChild = Children.toArray(children)[0];
  const className = isValidElement<{ className?: string }>(firstChild)
    ? firstChild.props.className
    : undefined;
  const language = className?.match(/(?:language|lang)-([\w-]+)/)?.[1];

  useEffect(() => {
    if (!copied) return;
    const timeout = window.setTimeout(() => setCopied(false), 1_500);
    return () => window.clearTimeout(timeout);
  }, [copied]);

  async function copyCode() {
    await copyText(code);
    setCopied(true);
  }

  return (
    <div className="markdown-code-block">
      <div className="markdown-code-header">
        <span>{language ?? "code"}</span>
        <button type="button" onClick={() => void copyCode()}>
          <Icon name={copied ? "check" : "copy"} size={13} />
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  );
}

function extractText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return extractText(node.props.children);
  return "";
}

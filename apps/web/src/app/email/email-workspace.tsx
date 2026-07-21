"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import {
  draftCommunicationReply,
  listCommunicationThreads,
  markCommunicationThreadRead,
  readCommunicationThread,
  replyToCommunicationThread,
  syncCommunicationAccount,
  type CommunicationAccount,
  type CommunicationThread,
  type CommunicationThreadDetail,
} from "../../lib/communication-api";
import { EmailMessageBody } from "../communications/email-message-body";
import { Icon, type IconName } from "../ui/icons";
import styles from "./email-workspace.module.css";

type SystemMailboxKey =
  | "inbox"
  | "sent"
  | "drafts"
  | "archive"
  | "spam"
  | "junk"
  | "trash";
type MailboxKey = SystemMailboxKey | "all";
type AiReplyTone = "positive" | "neutral" | "negative";

type MailboxDefinition = {
  key: SystemMailboxKey;
  label: string;
  icon: IconName;
};

const MAILBOXES: readonly MailboxDefinition[] = [
  { key: "inbox", label: "Inbox", icon: "inbox" },
  { key: "sent", label: "Sent", icon: "sent" },
  { key: "drafts", label: "Drafts", icon: "edit" },
  { key: "archive", label: "Archive", icon: "folder" },
  { key: "spam", label: "Spam", icon: "spam" },
  { key: "junk", label: "Junk", icon: "junk" },
  { key: "trash", label: "Trash", icon: "trash" },
];

const AI_REPLY_GUIDANCE: Record<AiReplyTone, string> = {
  positive:
    "Write a positive, friendly, and receptive reply. Express interest or agreement when supported by the thread. Do not invent commitments, dates, prices, or completed actions.",
  neutral:
    "Write a neutral, professional, and concise reply that directly addresses the latest relevant message. Ask for missing information only when it is necessary.",
  negative:
    "Write a polite but clear negative reply. Decline, disagree, or say the owner is not interested without being rude and without inventing reasons or commitments.",
};

const NAVIGATION_STORAGE_KEY = "aster.email-navigation-collapsed";
const MAILBOXES_STORAGE_KEY = "aster.email-mailboxes-open";
const FOLDERS_STORAGE_KEY = "aster.email-folders-open";

function storedBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const value = window.localStorage.getItem(key);
  return value === null ? fallback : value === "true";
}

function formatDate(value: string): string {
  const date = new Date(value);
  const now = new Date();
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  return new Intl.DateTimeFormat(
    undefined,
    sameDay ? { timeStyle: "short" } : { dateStyle: "medium" },
  ).format(date);
}

function senderLabel(message: CommunicationThreadDetail["messages"][number]): string {
  const name = message.sender_name?.trim();
  const address = message.sender_address?.trim();
  if (name && address) return `${name} <${address}>`;
  return name || address || "Unknown sender";
}

function recipientLabel(recipient: { name: string; address: string }): string {
  const name = recipient.name?.trim();
  const address = recipient.address?.trim();
  if (name && address) return `${name} <${address}>`;
  return name || address || "Unknown recipient";
}

function sourceId(thread: CommunicationThread): string {
  const source = thread.metadata.source_id;
  return typeof source === "string" ? source.trim() : "";
}

function normalizedSource(thread: CommunicationThread): string {
  return sourceId(thread)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase();
}

function systemMailboxForThread(thread: CommunicationThread): SystemMailboxKey | null {
  const source = normalizedSource(thread);
  if (!source) return "inbox";
  if (/sent|enviad|outbox/.test(source)) return "sent";
  if (/draft|rascunh/.test(source)) return "drafts";
  if (/archive|arquivo|all mail|todos os e-?mails/.test(source)) return "archive";
  if (/spam/.test(source)) return "spam";
  if (/junk|indesejad|bulk/.test(source)) return "junk";
  if (/trash|deleted|bin|lixeira/.test(source)) return "trash";
  if (/inbox|entrada|received/.test(source)) return "inbox";
  return null;
}

export function EmailWorkspace({
  initialAccounts,
  initialThreads,
  initialError,
}: {
  initialAccounts: CommunicationAccount[];
  initialThreads: CommunicationThread[];
  initialError: string | null;
}) {
  const [accounts] = useState(initialAccounts);
  const [threads, setThreads] = useState(initialThreads);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [thread, setThread] = useState<CommunicationThreadDetail | null>(null);
  const [threadLoading, setThreadLoading] = useState(false);
  const [mailbox, setMailbox] = useState<MailboxKey>("inbox");
  const [customFolder, setCustomFolder] = useState("");
  const [accountFilter, setAccountFilter] = useState("");
  const [query, setQuery] = useState("");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [navigationCollapsed, setNavigationCollapsed] = useState(() =>
    storedBoolean(NAVIGATION_STORAGE_KEY, false),
  );
  const [mailboxesOpen, setMailboxesOpen] = useState(() =>
    storedBoolean(MAILBOXES_STORAGE_KEY, true),
  );
  const [foldersOpen, setFoldersOpen] = useState(() =>
    storedBoolean(FOLDERS_STORAGE_KEY, true),
  );
  const [readerFocused, setReaderFocused] = useState(false);
  const [composerOpen, setComposerOpen] = useState(false);
  const [reply, setReply] = useState("");
  const [draftInstruction, setDraftInstruction] = useState("");
  const [activeTone, setActiveTone] = useState<AiReplyTone | null>(null);
  const [draftSource, setDraftSource] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);
  const replyRef = useRef<HTMLTextAreaElement>(null);
  const guidanceRef = useRef<HTMLInputElement>(null);

  const folderNames = useMemo(() => {
    const values = threads
      .filter((item) => systemMailboxForThread(item) === null)
      .map(sourceId)
      .filter(Boolean);
    return Array.from(new Set(values)).sort((left, right) => left.localeCompare(right));
  }, [threads]);

  const mailboxCounts = useMemo(() => {
    const counts: Record<MailboxKey, number> = {
      inbox: 0,
      sent: 0,
      drafts: 0,
      archive: 0,
      spam: 0,
      junk: 0,
      trash: 0,
      all: threads.length,
    };
    for (const item of threads) {
      const systemMailbox = systemMailboxForThread(item);
      if (systemMailbox) counts[systemMailbox] += 1;
    }
    return counts;
  }, [threads]);

  const visibleThreads = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return threads.filter((item) => {
      if (accountFilter && item.account_id !== accountFilter) return false;
      if (unreadOnly && item.unread_count === 0) return false;
      if (customFolder) {
        if (sourceId(item) !== customFolder) return false;
      } else if (mailbox !== "all" && systemMailboxForThread(item) !== mailbox) {
        return false;
      }
      if (!needle) return true;
      return `${item.title} ${item.preview} ${item.account_name}`
        .toLocaleLowerCase()
        .includes(needle);
    });
  }, [accountFilter, customFolder, mailbox, query, threads, unreadOnly]);

  useEffect(() => {
    if (selectedThreadId && !visibleThreads.some((item) => item.id === selectedThreadId)) {
      setSelectedThreadId(null);
      setThread(null);
      setThreadLoading(false);
      setComposerOpen(false);
    }
  }, [selectedThreadId, visibleThreads]);

  useEffect(() => {
    if (!selectedThreadId) {
      setThread(null);
      setThreadLoading(false);
      return;
    }
    let active = true;
    setThreadLoading(true);
    void readCommunicationThread(selectedThreadId)
      .then((detail) => {
        if (active) setThread(detail);
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Could not load the email thread.");
        }
      })
      .finally(() => {
        if (active) setThreadLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedThreadId]);

  async function refreshThreads() {
    setThreads(await listCommunicationThreads({ kind: "email" }));
  }

  function clearSelection() {
    setSelectedThreadId(null);
    setThread(null);
    setThreadLoading(false);
    setReaderFocused(false);
    setComposerOpen(false);
    setReply("");
    setDraftInstruction("");
    setActiveTone(null);
    setDraftSource(null);
  }

  function selectMailbox(nextMailbox: MailboxKey) {
    clearSelection();
    setMailbox(nextMailbox);
    setCustomFolder("");
    setNotice(null);
    setError(null);
  }

  function selectFolder(folder: string) {
    clearSelection();
    setCustomFolder(folder);
    setMailbox("all");
    setNotice(null);
    setError(null);
  }

  function selectAccount(accountId: string) {
    clearSelection();
    setAccountFilter(accountId);
    setNotice(null);
    setError(null);
  }

  function toggleNavigation() {
    setNavigationCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem(NAVIGATION_STORAGE_KEY, String(next));
      return next;
    });
  }

  function toggleMailboxes() {
    setMailboxesOpen((current) => {
      const next = !current;
      window.localStorage.setItem(MAILBOXES_STORAGE_KEY, String(next));
      return next;
    });
  }

  function toggleFolders() {
    setFoldersOpen((current) => {
      const next = !current;
      window.localStorage.setItem(FOLDERS_STORAGE_KEY, String(next));
      return next;
    });
  }

  function selectThread(threadId: string) {
    setSelectedThreadId(threadId);
    setThread(null);
    setThreadLoading(true);
    setComposerOpen(false);
    setReply("");
    setDraftInstruction("");
    setActiveTone(null);
    setDraftSource(null);
    setNotice(null);
    setError(null);
  }

  function focusReplyEditor() {
    setComposerOpen(true);
    window.requestAnimationFrame(() => replyRef.current?.focus());
  }

  function openManualReply() {
    setActiveTone(null);
    setDraftSource(null);
    focusReplyEditor();
  }

  function openCustomInstruction() {
    setComposerOpen(true);
    setActiveTone(null);
    window.requestAnimationFrame(() => guidanceRef.current?.focus());
  }

  async function syncAccounts() {
    const targets = accountFilter
      ? accounts.filter((account) => account.id === accountFilter)
      : accounts;
    if (!targets.length || busy) return;
    setBusy("sync");
    setNotice(null);
    setError(null);
    try {
      let added = 0;
      for (const account of targets) {
        const result = await syncCommunicationAccount(account.id);
        added += result.messages_added;
      }
      await refreshThreads();
      setNotice(`Sync complete: ${added} new message(s).`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not synchronize email.");
    } finally {
      setBusy(null);
    }
  }

  async function markRead() {
    if (!thread || busy) return;
    setBusy("read");
    setError(null);
    try {
      setThread(await markCommunicationThreadRead(thread.id));
      await refreshThreads();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not mark the thread read.");
    } finally {
      setBusy(null);
    }
  }

  async function generateDraft({
    instruction,
    tone,
  }: {
    instruction?: string;
    tone?: AiReplyTone;
  } = {}) {
    if (!thread || busy) return;
    const guidance = instruction?.trim() || AI_REPLY_GUIDANCE[tone ?? "neutral"];
    setComposerOpen(true);
    setActiveTone(tone ?? null);
    setDraftSource(null);
    setBusy("draft");
    setNotice(null);
    setError(null);
    try {
      const generated = await draftCommunicationReply(thread.id, guidance);
      setReply(generated.draft);
      setDraftSource(`${generated.model} via ${generated.endpoint}`);
      window.requestAnimationFrame(() => replyRef.current?.focus());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not generate a reply draft.");
    } finally {
      setBusy(null);
    }
  }

  async function sendReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!thread || !reply.trim() || busy) return;
    setBusy("reply");
    setNotice(null);
    setError(null);
    try {
      await replyToCommunicationThread(thread.id, reply);
      setReply("");
      setDraftInstruction("");
      setActiveTone(null);
      setDraftSource(null);
      setComposerOpen(false);
      setThread(await readCommunicationThread(thread.id));
      await refreshThreads();
      setNotice("Reply sent.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not send the reply.");
    } finally {
      setBusy(null);
    }
  }

  const currentMailboxLabel = customFolder
    ? customFolder
    : mailbox === "all"
      ? "All mail"
      : MAILBOXES.find((item) => item.key === mailbox)?.label ?? "Inbox";
  const workspaceClassName = [
    styles.workspace,
    navigationCollapsed ? styles.navigationCollapsed : "",
    readerFocused ? styles.readerFocused : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div aria-busy={Boolean(busy) || threadLoading} className={workspaceClassName}>
      <aside aria-label="Email mailboxes" className={styles.mailNavigation}>
        <div className={styles.navigationHeader}>
          <strong>Email</strong>
          <button aria-label="Collapse mailbox navigation" onClick={toggleNavigation} type="button">
            <Icon name="collapse-panel" size={15} />
          </button>
        </div>

        <section className={styles.navigationGroup}>
          <button
            aria-expanded={mailboxesOpen}
            className={styles.groupToggle}
            onClick={toggleMailboxes}
            type="button"
          >
            <Icon
              className={mailboxesOpen ? styles.chevronOpen : ""}
              name="chevron-right"
              size={13}
            />
            <span>Mailboxes</span>
          </button>
          {mailboxesOpen ? (
            <div className={styles.groupItems}>
              {MAILBOXES.map((item) => (
                <button
                  aria-current={!customFolder && mailbox === item.key ? "page" : undefined}
                  className={!customFolder && mailbox === item.key ? styles.activeMailbox : ""}
                  key={item.key}
                  onClick={() => selectMailbox(item.key)}
                  type="button"
                >
                  <Icon name={item.icon} size={15} />
                  <span>{item.label}</span>
                  <small>{mailboxCounts[item.key]}</small>
                </button>
              ))}
              <button
                aria-current={!customFolder && mailbox === "all" ? "page" : undefined}
                className={!customFolder && mailbox === "all" ? styles.activeMailbox : ""}
                onClick={() => selectMailbox("all")}
                type="button"
              >
                <Icon name="email" size={15} />
                <span>All mail</span>
                <small>{mailboxCounts.all}</small>
              </button>
            </div>
          ) : null}
        </section>

        <section className={styles.navigationGroup}>
          <button
            aria-expanded={foldersOpen}
            className={styles.groupToggle}
            onClick={toggleFolders}
            type="button"
          >
            <Icon
              className={foldersOpen ? styles.chevronOpen : ""}
              name="chevron-right"
              size={13}
            />
            <span>Folders</span>
          </button>
          {foldersOpen ? (
            <div className={styles.groupItems}>
              {folderNames.length ? (
                folderNames.map((folder) => (
                  <button
                    aria-current={customFolder === folder ? "page" : undefined}
                    className={customFolder === folder ? styles.activeMailbox : ""}
                    key={folder}
                    onClick={() => selectFolder(folder)}
                    type="button"
                  >
                    <Icon name="folder" size={15} />
                    <span title={folder}>{folder}</span>
                    <small>{threads.filter((item) => sourceId(item) === folder).length}</small>
                  </button>
                ))
              ) : (
                <p>No additional synchronized folders.</p>
              )}
            </div>
          ) : null}
        </section>

        <section className={styles.accountSection}>
          <p>Accounts</p>
          <button
            className={!accountFilter ? styles.activeAccount : ""}
            onClick={() => selectAccount("")}
            type="button"
          >
            <span>All accounts</span>
            <small>{accounts.length}</small>
          </button>
          {accounts.map((account) => (
            <button
              className={accountFilter === account.id ? styles.activeAccount : ""}
              key={account.id}
              onClick={() => selectAccount(account.id)}
              type="button"
            >
              <span>{account.name}</span>
              <small>{account.enabled ? "On" : "Off"}</small>
            </button>
          ))}
        </section>

        <Link className={styles.manageLink} href="/email/settings">
          <Icon name="settings" size={14} />
          Manage email accounts and rules
        </Link>
      </aside>

      <section aria-label={`${currentMailboxLabel} messages`} className={styles.threadColumn}>
        <header className={styles.threadToolbar}>
          {navigationCollapsed ? (
            <button aria-label="Expand mailbox navigation" onClick={toggleNavigation} type="button">
              <Icon name="expand-panel" size={15} />
            </button>
          ) : null}
          <div>
            <strong>{currentMailboxLabel}</strong>
            <span>{visibleThreads.length} conversation(s)</span>
          </div>
          <button
            disabled={!accounts.length || Boolean(busy)}
            onClick={() => void syncAccounts()}
            type="button"
          >
            <Icon name="refresh" size={14} />
            <span>{busy === "sync" ? "Syncing…" : "Sync"}</span>
          </button>
        </header>

        <form className={styles.filters} onSubmit={(event) => event.preventDefault()}>
          <div>
            <Icon name="search" size={14} />
            <input
              aria-label="Search email"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search messages"
              value={query}
            />
          </div>
          <label>
            <input
              checked={unreadOnly}
              onChange={(event) => setUnreadOnly(event.target.checked)}
              type="checkbox"
            />
            Unread
          </label>
        </form>

        {notice ? <div className={styles.notice}>{notice}</div> : null}
        {error ? <div className={styles.error}>{error}</div> : null}

        <div className={styles.threadList}>
          {visibleThreads.length ? (
            visibleThreads.map((item) => (
              <button
                aria-pressed={selectedThreadId === item.id}
                className={selectedThreadId === item.id ? styles.selectedThread : ""}
                key={item.id}
                onClick={() => selectThread(item.id)}
                type="button"
              >
                <header>
                  <strong>{item.title}</strong>
                  <time>{formatDate(item.last_message_at)}</time>
                </header>
                <div>
                  <span>{item.account_name}</span>
                  {item.unread_count ? <small>{item.unread_count}</small> : null}
                </div>
                <p>{item.preview || "No text content"}</p>
              </button>
            ))
          ) : (
            <div className={styles.emptyState}>
              <Icon name="inbox" size={22} />
              <strong>No messages here.</strong>
              <span>Choose another mailbox or synchronize an email account.</span>
            </div>
          )}
        </div>
      </section>

      <article className={styles.reader}>
        {threadLoading ? (
          <div className={styles.emptyState}>
            <strong>Loading email…</strong>
          </div>
        ) : !thread ? (
          <div className={styles.emptyState}>
            <Icon name="email" size={24} />
            <strong>Select a conversation.</strong>
            <span>The complete email thread will open here.</span>
          </div>
        ) : (
          <>
            <header className={styles.readerHeader}>
              <div>
                <p>{thread.account_name}</p>
                <h1>{thread.title}</h1>
                <span>
                  {thread.message_count} message(s) · {thread.participants.length} participant(s)
                </span>
              </div>
              <div className={styles.readerActions}>
                <button
                  aria-label={readerFocused ? "Restore email columns" : "Focus email reader"}
                  aria-pressed={readerFocused}
                  onClick={() => setReaderFocused((current) => !current)}
                  title={readerFocused ? "Restore columns" : "Focus reader"}
                  type="button"
                >
                  <Icon name={readerFocused ? "unfocus" : "focus"} size={14} />
                  <span>{readerFocused ? "Restore" : "Focus"}</span>
                </button>
                {thread.unread_count ? (
                  <button disabled={Boolean(busy)} onClick={() => void markRead()} type="button">
                    Mark read
                  </button>
                ) : null}
                <button
                  className={styles.primaryReply}
                  disabled={Boolean(busy)}
                  onClick={openManualReply}
                  type="button"
                >
                  <Icon name="reply" size={14} />
                  Reply
                </button>
              </div>
            </header>

            <section aria-label="AI reply actions" className={styles.replyActionBar}>
              <div className={styles.aiActionIntro}>
                <Icon name="persona" size={15} />
                <div>
                  <strong>Reply with AI</strong>
                  <span>Creates an editable draft. It never sends automatically.</span>
                </div>
              </div>
              <div className={styles.aiActionButtons}>
                <button
                  aria-pressed={activeTone === "neutral"}
                  disabled={Boolean(busy)}
                  onClick={() => void generateDraft({ tone: "neutral" })}
                  type="button"
                >
                  <Icon name="persona" size={13} />
                  {busy === "draft" && activeTone === "neutral" ? "Drafting…" : "AI reply"}
                </button>
                <button
                  aria-pressed={activeTone === "positive"}
                  className={styles.positiveAction}
                  disabled={Boolean(busy)}
                  onClick={() => void generateDraft({ tone: "positive" })}
                  type="button"
                >
                  <Icon name="positive" size={13} />
                  {busy === "draft" && activeTone === "positive" ? "Drafting…" : "Positive"}
                </button>
                <button
                  aria-pressed={activeTone === "negative"}
                  className={styles.negativeAction}
                  disabled={Boolean(busy)}
                  onClick={() => void generateDraft({ tone: "negative" })}
                  type="button"
                >
                  <Icon name="negative" size={13} />
                  {busy === "draft" && activeTone === "negative" ? "Drafting…" : "Negative"}
                </button>
                <button disabled={Boolean(busy)} onClick={openCustomInstruction} type="button">
                  <Icon name="edit" size={13} />
                  Custom
                </button>
              </div>
            </section>

            <div className={styles.messageList}>
              {thread.messages.map((message) => (
                <section className={styles.message} key={message.id}>
                  <header>
                    <div>
                      <strong>{senderLabel(message)}</strong>
                      <span>{message.direction}</span>
                    </div>
                    <time>{formatDate(message.sent_at)}</time>
                  </header>
                  {message.recipients.length ? (
                    <p>To: {message.recipients.map(recipientLabel).join(", ")}</p>
                  ) : null}
                  {message.subject && message.subject !== thread.title ? (
                    <h2>{message.subject}</h2>
                  ) : null}
                  <EmailMessageBody message={message} threadKind="email" />
                  {message.attachments.length ? (
                    <div className={styles.attachments}>
                      {message.attachments.map((attachment) => (
                        <a href={attachment.content_path} key={attachment.id}>
                          {attachment.filename} · {Math.ceil(attachment.size_bytes / 1024)} KB
                        </a>
                      ))}
                    </div>
                  ) : null}
                </section>
              ))}
            </div>

            {composerOpen ? (
              <form className={styles.replyComposer} onSubmit={(event) => void sendReply(event)}>
                <header className={styles.replyComposerHeader}>
                  <div>
                    <Icon name="reply" size={15} />
                    <div>
                      <strong>Reply</strong>
                      <span>
                        {busy === "draft"
                          ? "Aster is drafting an editable reply…"
                          : draftSource
                            ? `AI draft · ${draftSource}`
                            : "Manual draft · nothing is sent automatically"}
                      </span>
                    </div>
                  </div>
                  <button
                    aria-label="Hide reply editor"
                    disabled={busy === "reply"}
                    onClick={() => setComposerOpen(false)}
                    type="button"
                  >
                    <Icon name="close" size={14} />
                  </button>
                </header>

                <section className={styles.aiPrompt}>
                  <label htmlFor="email-ai-guidance">
                    <Icon name="persona" size={13} />
                    Tell Aster how to answer
                  </label>
                  <div className={styles.draftTools}>
                    <input
                      id="email-ai-guidance"
                      maxLength={4000}
                      onChange={(event) => setDraftInstruction(event.target.value)}
                      placeholder="Example: Say I want more information and ask about pricing."
                      ref={guidanceRef}
                      value={draftInstruction}
                    />
                    <button
                      disabled={Boolean(busy)}
                      onClick={() => void generateDraft({ instruction: draftInstruction })}
                      type="button"
                    >
                      <Icon name="persona" size={13} />
                      {busy === "draft" && activeTone === null
                        ? "Generating…"
                        : reply.trim()
                          ? "Rewrite"
                          : "Generate"}
                    </button>
                  </div>
                </section>

                {error ? <div className={styles.composerError}>{error}</div> : null}

                <textarea
                  aria-label="Reply draft"
                  onChange={(event) => setReply(event.target.value)}
                  placeholder="Write or review the reply here. Nothing is sent until you press Send reply."
                  ref={replyRef}
                  rows={5}
                  value={reply}
                />
                <footer>
                  <span>Review and edit the final text before sending.</span>
                  <button disabled={!reply.trim() || Boolean(busy)} type="submit">
                    <Icon name="sent" size={13} />
                    {busy === "reply" ? "Sending…" : "Send reply"}
                  </button>
                </footer>
              </form>
            ) : null}
          </>
        )}
      </article>
    </div>
  );
}

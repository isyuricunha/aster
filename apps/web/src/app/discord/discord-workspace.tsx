"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";

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
import { Icon } from "../ui/icons";
import styles from "./discord-workspace.module.css";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function sourceId(thread: CommunicationThread): string {
  const value = thread.metadata.source_id;
  return typeof value === "string" ? value : "";
}

function senderLabel(message: CommunicationThreadDetail["messages"][number]): string {
  return message.sender_name?.trim() || message.sender_address?.trim() || "Unknown user";
}

export function DiscordWorkspace({
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
  const [accountFilter, setAccountFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [query, setQuery] = useState("");
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(initialThreads[0]?.id ?? null);
  const [thread, setThread] = useState<CommunicationThreadDetail | null>(null);
  const [threadLoading, setThreadLoading] = useState(Boolean(initialThreads[0]));
  const [reply, setReply] = useState("");
  const [draftInstruction, setDraftInstruction] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);

  const channels = useMemo(() => {
    const labels = threads.map(sourceId).filter(Boolean);
    return Array.from(new Set(labels)).sort((left, right) => left.localeCompare(right));
  }, [threads]);

  const visibleThreads = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return threads.filter((item) => {
      if (accountFilter && item.account_id !== accountFilter) return false;
      if (channelFilter && sourceId(item) !== channelFilter) return false;
      if (!needle) return true;
      return `${item.title} ${item.preview} ${item.account_name}`.toLocaleLowerCase().includes(needle);
    });
  }, [accountFilter, channelFilter, query, threads]);

  useEffect(() => {
    if (!selectedThreadId || !visibleThreads.some((item) => item.id === selectedThreadId)) {
      const next = visibleThreads[0]?.id ?? null;
      setSelectedThreadId(next);
      setThread(null);
      setThreadLoading(Boolean(next));
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
        if (active) setError(caught instanceof Error ? caught.message : "Could not load the Discord thread.");
      })
      .finally(() => {
        if (active) setThreadLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedThreadId]);

  async function refreshThreads() {
    setThreads(await listCommunicationThreads({ kind: "discord" }));
  }

  function selectThread(threadId: string) {
    setSelectedThreadId(threadId);
    setThread(null);
    setThreadLoading(true);
    setReply("");
    setDraftInstruction("");
    setNotice(null);
    setError(null);
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
      setError(caught instanceof Error ? caught.message : "Could not synchronize Discord.");
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

  async function generateDraft() {
    if (!thread || busy) return;
    setBusy("draft");
    setNotice(null);
    setError(null);
    try {
      const generated = await draftCommunicationReply(thread.id, draftInstruction);
      setReply(generated.draft);
      setNotice(`Draft generated with ${generated.model}. Review it before sending.`);
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
      setThread(await readCommunicationThread(thread.id));
      await refreshThreads();
      setNotice("Reply sent.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not send the Discord reply.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={styles.workspace} aria-busy={Boolean(busy) || threadLoading}>
      <aside className={styles.channelRail}>
        <header>
          <Icon name="discord" size={16} />
          <strong>Discord</strong>
        </header>

        <section>
          <p>Accounts</p>
          <button
            className={!accountFilter ? styles.activeRailItem : ""}
            onClick={() => setAccountFilter("")}
            type="button"
          >
            <Icon name="discord" size={14} />
            <span>All accounts</span>
            <small>{accounts.length}</small>
          </button>
          {accounts.map((account) => (
            <button
              className={accountFilter === account.id ? styles.activeRailItem : ""}
              key={account.id}
              onClick={() => setAccountFilter(account.id)}
              type="button"
            >
              <span className={styles.statusDot} data-enabled={account.enabled} />
              <span>{account.name}</span>
            </button>
          ))}
        </section>

        <section>
          <p>Channels</p>
          <button
            className={!channelFilter ? styles.activeRailItem : ""}
            onClick={() => setChannelFilter("")}
            type="button"
          >
            <Icon name="hash" size={14} />
            <span>All channels</span>
            <small>{channels.length}</small>
          </button>
          {channels.map((channel) => (
            <button
              className={channelFilter === channel ? styles.activeRailItem : ""}
              key={channel}
              onClick={() => setChannelFilter(channel)}
              type="button"
            >
              <Icon name="hash" size={14} />
              <span title={channel}>{channel}</span>
            </button>
          ))}
        </section>

        <Link href="/communications">
          <Icon name="settings" size={14} />
          Manage connections and rules
        </Link>
      </aside>

      <section className={styles.threadColumn}>
        <header className={styles.threadToolbar}>
          <div>
            <strong>{channelFilter || "Conversations"}</strong>
            <span>{visibleThreads.length} thread(s)</span>
          </div>
          <button disabled={!accounts.length || Boolean(busy)} onClick={() => void syncAccounts()} type="button">
            <Icon name="refresh" size={14} />
            <span>{busy === "sync" ? "Syncing…" : "Sync"}</span>
          </button>
        </header>
        <div className={styles.searchBox}>
          <Icon name="search" size={14} />
          <input
            aria-label="Search Discord messages"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search channels and messages"
            value={query}
          />
        </div>
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
                  {item.unread_count ? <small>{item.unread_count}</small> : null}
                </header>
                <span>
                  <Icon name="hash" size={11} /> {sourceId(item) || item.account_name}
                </span>
                <p>{item.preview || "No text content"}</p>
              </button>
            ))
          ) : (
            <div className={styles.emptyState}>
              <strong>No Discord messages here.</strong>
              <span>Choose another channel or synchronize an account.</span>
            </div>
          )}
        </div>
      </section>

      <article className={styles.chatPane}>
        {threadLoading ? (
          <div className={styles.emptyState}>
            <strong>Loading Discord thread…</strong>
          </div>
        ) : !thread ? (
          <div className={styles.emptyState}>
            <Icon name="discord" size={24} />
            <strong>Select a Discord conversation.</strong>
            <span>Messages and reply controls will appear here.</span>
          </div>
        ) : (
          <>
            <header className={styles.chatHeader}>
              <div>
                <span>
                  <Icon name="hash" size={14} /> {sourceId(thread) || thread.account_name}
                </span>
                <h1>{thread.title}</h1>
              </div>
              {thread.unread_count ? (
                <button disabled={Boolean(busy)} onClick={() => void markRead()} type="button">
                  Mark read
                </button>
              ) : null}
            </header>

            <div className={styles.messageList}>
              {thread.messages.map((message) => (
                <section className={message.direction === "outbound" ? styles.outbound : ""} key={message.id}>
                  <div className={styles.avatar}>{senderLabel(message).slice(0, 1).toUpperCase()}</div>
                  <div>
                    <header>
                      <strong>{senderLabel(message)}</strong>
                      <time>{formatDate(message.sent_at)}</time>
                    </header>
                    <p>{message.content_text || "No text content"}</p>
                    {message.attachments.length ? (
                      <div className={styles.attachments}>
                        {message.attachments.map((attachment) => (
                          <a href={attachment.content_path} key={attachment.id}>
                            {attachment.filename}
                          </a>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </section>
              ))}
            </div>

            <form className={styles.composer} onSubmit={(event) => void sendReply(event)}>
              <div>
                <input
                  maxLength={4000}
                  onChange={(event) => setDraftInstruction(event.target.value)}
                  placeholder="Optional AI guidance"
                  value={draftInstruction}
                />
                <button disabled={Boolean(busy)} onClick={() => void generateDraft()} type="button">
                  {busy === "draft" ? "Drafting…" : "Draft with AI"}
                </button>
              </div>
              <textarea
                aria-label="Discord reply"
                onChange={(event) => setReply(event.target.value)}
                placeholder="Message this channel"
                rows={4}
                value={reply}
              />
              <footer>
                <span>Mentions remain disabled by the API.</span>
                <button disabled={!reply.trim() || Boolean(busy)} type="submit">
                  {busy === "reply" ? "Sending…" : "Send"}
                </button>
              </footer>
            </form>
          </>
        )}
      </article>
    </div>
  );
}

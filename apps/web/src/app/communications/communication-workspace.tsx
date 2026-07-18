"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import type { Automation, IntegrationConnection } from "../../lib/automation-api";
import {
  listCommunicationThreads,
  markCommunicationThreadRead,
  readCommunicationThread,
  replyToCommunicationThread,
  syncCommunicationAccount,
  type CommunicationAccount,
  type CommunicationRule,
  type CommunicationThread,
  type CommunicationThreadDetail,
  type CommunicationThreadKind,
} from "../../lib/communication-api";
import { AccountPanel } from "./account-panel";
import { RulePanel } from "./rule-panel";
import styles from "./communications.module.css";

type Tab = "inbox" | "accounts" | "rules";

const TABS: Tab[] = ["inbox", "accounts", "rules"];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function senderLabel(message: CommunicationThreadDetail["messages"][number]): string {
  return message.sender_name || message.sender_address || "Unknown sender";
}

export function CommunicationWorkspace({
  initialAccounts,
  initialThreads,
  initialRules,
  automations,
  integrations,
  initialError,
}: {
  initialAccounts: CommunicationAccount[];
  initialThreads: CommunicationThread[];
  initialRules: CommunicationRule[];
  automations: Automation[];
  integrations: IntegrationConnection[];
  initialError: string | null;
}) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [tab, setTab] = useState<Tab>("inbox");
  const [accounts, setAccounts] = useState(initialAccounts);
  const [threads, setThreads] = useState(initialThreads);
  const [rules, setRules] = useState(initialRules);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(
    initialThreads[0]?.id ?? null,
  );
  const [thread, setThread] = useState<CommunicationThreadDetail | null>(null);
  const [threadLoading, setThreadLoading] = useState(Boolean(initialThreads[0]));
  const [threadRefreshKey, setThreadRefreshKey] = useState(0);
  const [accountFilter, setAccountFilter] = useState("");
  const [kindFilter, setKindFilter] = useState<CommunicationThreadKind | "">("");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);

  const unreadCount = useMemo(
    () => threads.reduce((total, item) => total + item.unread_count, 0),
    [threads],
  );
  const selectedAccount = accounts.find((account) => account.id === accountFilter) ?? null;

  function selectTab(nextTab: Tab, focus = false) {
    setTab(nextTab);
    if (focus) {
      tabRefs.current[TABS.indexOf(nextTab)]?.focus();
    }
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % TABS.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + TABS.length) % TABS.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = TABS.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    selectTab(TABS[nextIndex], true);
  }

  useEffect(() => {
    if (!selectedThreadId) return;
    let active = true;
    void readCommunicationThread(selectedThreadId)
      .then((detail) => {
        if (active) setThread(detail);
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Could not load the thread.");
        }
      })
      .finally(() => {
        if (active) setThreadLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedThreadId, threadRefreshKey]);

  async function refreshInbox(nextQuery = query) {
    const next = await listCommunicationThreads({
      accountId: accountFilter || undefined,
      kind: kindFilter,
      unreadOnly,
      query: nextQuery,
    });
    setThreads(next);
    const nextSelectedThreadId =
      selectedThreadId && next.some((item) => item.id === selectedThreadId)
        ? selectedThreadId
        : next[0]?.id ?? null;
    setThread(null);
    setThreadLoading(Boolean(nextSelectedThreadId));
    setSelectedThreadId(nextSelectedThreadId);
    setThreadRefreshKey((current) => current + 1);
  }

  function selectThread(threadId: string) {
    setThread(null);
    setThreadLoading(true);
    setError(null);
    if (threadId === selectedThreadId) {
      setThreadRefreshKey((current) => current + 1);
      return;
    }
    setSelectedThreadId(threadId);
  }

  async function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy("filter");
    setError(null);
    try {
      await refreshInbox();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not refresh the inbox.");
    } finally {
      setBusy(null);
    }
  }

  async function syncAccount() {
    const account = selectedAccount ?? accounts[0];
    if (!account || busy) return;
    setBusy("sync");
    setNotice(null);
    setError(null);
    try {
      const result = await syncCommunicationAccount(account.id);
      await refreshInbox();
      setNotice(
        `Sync complete: ${result.messages_added} new message(s), ${result.automations_enqueued} automation(s) queued.`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not synchronize the account.");
    } finally {
      setBusy(null);
    }
  }

  async function markRead() {
    if (!thread || busy) return;
    setBusy("read");
    setError(null);
    try {
      const updated = await markCommunicationThreadRead(thread.id);
      setThread(updated);
      await refreshInbox();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not mark the thread read.");
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
      setThread(await readCommunicationThread(thread.id));
      await refreshInbox();
      setNotice("Reply sent.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not send the reply.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={styles.workspace} aria-busy={Boolean(busy) || threadLoading}>
      <div className={styles.tabs} aria-label="Communication sections" role="tablist">
        <button
          aria-controls="communication-panel-inbox"
          aria-selected={tab === "inbox"}
          className={tab === "inbox" ? styles.activeTab : ""}
          id="communication-tab-inbox"
          onClick={() => selectTab("inbox")}
          onKeyDown={(event) => handleTabKeyDown(event, 0)}
          ref={(element) => {
            tabRefs.current[0] = element;
          }}
          role="tab"
          tabIndex={tab === "inbox" ? 0 : -1}
          type="button"
        >
          Inbox <span>{unreadCount}</span>
        </button>
        <button
          aria-controls="communication-panel-accounts"
          aria-selected={tab === "accounts"}
          className={tab === "accounts" ? styles.activeTab : ""}
          id="communication-tab-accounts"
          onClick={() => selectTab("accounts")}
          onKeyDown={(event) => handleTabKeyDown(event, 1)}
          ref={(element) => {
            tabRefs.current[1] = element;
          }}
          role="tab"
          tabIndex={tab === "accounts" ? 0 : -1}
          type="button"
        >
          Accounts <span>{accounts.length}</span>
        </button>
        <button
          aria-controls="communication-panel-rules"
          aria-selected={tab === "rules"}
          className={tab === "rules" ? styles.activeTab : ""}
          id="communication-tab-rules"
          onClick={() => selectTab("rules")}
          onKeyDown={(event) => handleTabKeyDown(event, 2)}
          ref={(element) => {
            tabRefs.current[2] = element;
          }}
          role="tab"
          tabIndex={tab === "rules" ? 0 : -1}
          type="button"
        >
          Rules <span>{rules.length}</span>
        </button>
      </div>

      {tab === "inbox" ? (
        <section
          aria-labelledby="communication-tab-inbox"
          className={styles.inbox}
          id="communication-panel-inbox"
          role="tabpanel"
        >
          <form className={styles.inboxToolbar} onSubmit={(event) => void applyFilters(event)}>
            <select
              aria-label="Filter by account"
              onChange={(event) => setAccountFilter(event.target.value)}
              value={accountFilter}
            >
              <option value="">All accounts</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by communication type"
              onChange={(event) =>
                setKindFilter(event.target.value as CommunicationThreadKind | "")
              }
              value={kindFilter}
            >
              <option value="">Email and Discord</option>
              <option value="email">Email</option>
              <option value="discord">Discord</option>
            </select>
            <input
              aria-label="Search messages"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search subject, sender, or message"
              value={query}
            />
            <label className={styles.check}>
              <input
                checked={unreadOnly}
                onChange={(event) => setUnreadOnly(event.target.checked)}
                type="checkbox"
              />
              Unread only
            </label>
            <button disabled={Boolean(busy)} type="submit">
              Apply
            </button>
            <button
              disabled={!accounts.length || Boolean(busy)}
              onClick={() => void syncAccount()}
              type="button"
            >
              {busy === "sync"
                ? "Syncing…"
                : `Sync ${selectedAccount?.name ?? accounts[0]?.name ?? "account"}`}
            </button>
          </form>

          {notice ? <div className={styles.notice} role="status">{notice}</div> : null}
          {error ? <div className={styles.error} role="alert">{error}</div> : null}

          <div className={styles.inboxLayout}>
            <aside aria-label="Message threads" className={styles.threadList}>
              {threads.length === 0 ? (
                <div className={styles.emptyState}>
                  <strong>No messages yet.</strong>
                  <span>Add an account or synchronize an existing one.</span>
                </div>
              ) : null}
              {threads.map((item) => (
                <button
                  aria-pressed={selectedThreadId === item.id}
                  className={selectedThreadId === item.id ? styles.selectedThread : ""}
                  key={item.id}
                  onClick={() => selectThread(item.id)}
                  type="button"
                >
                  <header>
                    <strong>{item.title}</strong>
                    {item.unread_count ? <span>{item.unread_count}</span> : null}
                  </header>
                  <small>{item.account_name} · {item.kind}</small>
                  <p>{item.preview || "No text content"}</p>
                  <time>{formatDate(item.last_message_at)}</time>
                </button>
              ))}
            </aside>

            <article className={styles.threadDetail}>
              {threadLoading ? (
                <div className={styles.emptyState} role="status">
                  <strong>Loading thread…</strong>
                  <span>Messages and reply controls will appear when it is ready.</span>
                </div>
              ) : !selectedThreadId ? (
                <div className={styles.emptyState}>
                  <strong>Select a thread.</strong>
                  <span>Messages and manual reply controls appear here.</span>
                </div>
              ) : !thread ? (
                <div className={styles.emptyState}>
                  <strong>Thread unavailable.</strong>
                  <span>Select the thread again to retry loading it.</span>
                </div>
              ) : (
                <>
                  <header className={styles.threadHeader}>
                    <div>
                      <p>{thread.account_name} · {thread.kind}</p>
                      <h2>{thread.title}</h2>
                      <span>{thread.message_count} message(s)</span>
                    </div>
                    {thread.unread_count ? (
                      <button
                        disabled={Boolean(busy)}
                        onClick={() => void markRead()}
                        type="button"
                      >
                        Mark read
                      </button>
                    ) : null}
                  </header>

                  <div className={styles.messageList}>
                    {thread.messages.map((message) => (
                      <section
                        className={
                          message.direction === "outbound"
                            ? styles.outboundMessage
                            : styles.inboundMessage
                        }
                        key={message.id}
                      >
                        <header>
                          <div>
                            <strong>{senderLabel(message)}</strong>
                            <span>{message.direction}</span>
                          </div>
                          <time>{formatDate(message.sent_at)}</time>
                        </header>
                        {message.subject && message.subject !== thread.title ? (
                          <h3>{message.subject}</h3>
                        ) : null}
                        <pre>{message.content_text || "No text content"}</pre>
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

                  <form className={styles.replyBox} onSubmit={(event) => void sendReply(event)}>
                    <label>
                      Manual reply
                      <textarea
                        onChange={(event) => setReply(event.target.value)}
                        placeholder="Nothing is sent until you press Send reply."
                        rows={5}
                        value={reply}
                      />
                    </label>
                    <div>
                      <span>
                        Communication automations do not inherit permission to reply to this thread.
                      </span>
                      <button disabled={!reply.trim() || Boolean(busy)} type="submit">
                        {busy === "reply" ? "Sending…" : "Send reply"}
                      </button>
                    </div>
                  </form>
                </>
              )}
            </article>
          </div>
        </section>
      ) : null}

      {tab === "accounts" ? (
        <div
          aria-labelledby="communication-tab-accounts"
          id="communication-panel-accounts"
          role="tabpanel"
        >
          <AccountPanel
            initialAccounts={accounts}
            integrations={integrations}
            onAccountsChange={setAccounts}
            onInboxChange={refreshInbox}
          />
        </div>
      ) : null}

      {tab === "rules" ? (
        <div
          aria-labelledby="communication-tab-rules"
          id="communication-panel-rules"
          role="tabpanel"
        >
          <RulePanel
            initialRules={rules}
            accounts={accounts}
            automations={automations}
            onRulesChange={setRules}
          />
        </div>
      ) : null}
    </div>
  );
}

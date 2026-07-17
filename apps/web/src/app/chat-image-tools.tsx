"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";

import type { Conversation, ModelPreferences } from "../lib/api";
import {
  createImageOperation,
  listImageProfiles,
  uploadImageAsset,
  type ImageModelProfile,
  type MediaAsset,
  type MessageAttachment,
} from "../lib/image-api";
import { Icon } from "./ui/icons";
import styles from "./chat-images.module.css";

export function MessageAttachments({
  attachments,
  disabled,
  onEdit,
}: {
  attachments: MessageAttachment[];
  disabled: boolean;
  onEdit: (asset: MediaAsset) => void;
}) {
  if (!attachments.length) return null;
  return (
    <div className={styles.messageAttachments}>
      {attachments.map((attachment) => (
        <figure key={attachment.id}>
          <a href={attachment.content_url} target="_blank">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt={attachment.attachment_type === "output" ? "Generated image" : "Image input"} src={attachment.content_url} />
          </a>
          <figcaption>
            <span>{attachment.width}×{attachment.height}</span>
            <button disabled={disabled} onClick={() => onEdit(attachment)} type="button">
              <Icon name="edit" size={12} />
              Edit
            </button>
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

export function ChatImageComposer({
  disabled,
  conversation,
  preferences,
  editAsset,
  ensureConversation,
  onClearEdit,
  onCompleted,
  onError,
}: {
  disabled: boolean;
  conversation: Conversation | null;
  preferences: ModelPreferences | null;
  editAsset: MediaAsset | null;
  ensureConversation: () => Promise<Conversation>;
  onClearEdit: () => void;
  onCompleted: (conversationId: string) => Promise<void>;
  onError: (message: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [profiles, setProfiles] = useState<ImageModelProfile[]>([]);
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [mask, setMask] = useState<File | null>(null);
  const [size, setSize] = useState("");
  const [quality, setQuality] = useState("");
  const [format, setFormat] = useState<"png" | "jpeg" | "webp" | "">("");
  const [count, setCount] = useState(1);
  const [background, setBackground] = useState("");
  const [inputFidelity, setInputFidelity] = useState("");
  const [providerParameters, setProviderParameters] = useState("{}");
  const [advanced, setAdvanced] = useState(false);
  const [working, setWorking] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const maskRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void listImageProfiles().then(setProfiles).catch(() => setProfiles([]));
  }, []);
  useEffect(() => {
    if (editAsset) setOpen(true);
  }, [editAsset]);

  const selectedModel = preferences?.image ?? preferences?.primary ?? null;
  const profile = useMemo(
    () => profiles.find((item) => item.model_id === selectedModel?.id) ?? null,
    [profiles, selectedModel],
  );
  const inputCount = files.length + (editAsset ? 1 : 0);
  const editing = inputCount > 0;
  const capable = Boolean(
    selectedModel &&
      profile?.endpoint_enabled &&
      profile.is_available &&
      (editing ? profile.supports_editing : profile.supports_generation),
  );

  function addFiles(event: ChangeEvent<HTMLInputElement>) {
    const incoming = Array.from(event.target.files ?? []);
    event.target.value = "";
    setFiles((current) => [...current, ...incoming].slice(0, profile?.max_input_images ?? 8));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim() || disabled || working || !capable) return;
    setWorking(true);
    onError("");
    const uploaded: MediaAsset[] = [];
    try {
      if (editAsset) uploaded.push(editAsset);
      for (const file of files) uploaded.push(await uploadImageAsset(file));
      const uploadedMask = mask ? await uploadImageAsset(mask) : null;
      const extras = JSON.parse(providerParameters || "{}") as unknown;
      if (!extras || Array.isArray(extras) || typeof extras !== "object") {
        throw new Error("Provider parameters must be a JSON object.");
      }
      const target = conversation ?? (await ensureConversation());
      await createImageOperation(target.id, {
        prompt: prompt.trim(),
        input_asset_ids: uploaded.map((asset) => asset.id),
        mask_asset_id: uploadedMask?.id ?? null,
        size: size.trim() || null,
        quality: quality.trim() || null,
        output_format: format || null,
        background: background.trim() || null,
        count,
        input_fidelity: inputFidelity.trim() || null,
        provider_parameters: extras as Record<string, unknown>,
      });
      setPrompt("");
      setFiles([]);
      setMask(null);
      onClearEdit();
      await onCompleted(target.id);
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not complete the image operation.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className={styles.composerExtension}>
      <button
        className={`${styles.toggle} ${open ? styles.active : ""}`}
        disabled={disabled}
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        <Icon name="images" size={14} />
        Image
      </button>
      {open ? (
        <form className={styles.panel} onSubmit={(event) => void submit(event)}>
          <div className={styles.panelHeading}>
            <div>
              <strong>{editing ? "Edit images" : "Generate images"}</strong>
              <span>
                {selectedModel
                  ? `${selectedModel.endpoint_name} / ${selectedModel.model_id}`
                  : "No image model selected"}
              </span>
            </div>
            {!capable ? <Link href="/images">Configure capabilities</Link> : null}
          </div>

          {editAsset ? (
            <div className={styles.editAsset}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img alt="Selected image to edit" src={editAsset.content_url} />
              <div><strong>Editing gallery image</strong><span>{editAsset.width}×{editAsset.height}</span></div>
              <button onClick={onClearEdit} type="button"><Icon name="close" size={13} /></button>
            </div>
          ) : null}

          {files.length ? (
            <div className={styles.fileList}>
              {files.map((file, index) => (
                <span key={`${file.name}-${file.size}-${index}`}>
                  {file.name}
                  <button onClick={() => setFiles((current) => current.filter((_, item) => item !== index))} type="button"><Icon name="close" size={11} /></button>
                </span>
              ))}
            </div>
          ) : null}

          <textarea
            disabled={disabled || working}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={editing ? "Describe the changes to make…" : "Describe the image to generate…"}
            rows={3}
            value={prompt}
          />

          <div className={styles.actions}>
            <button onClick={() => fileRef.current?.click()} type="button">
              <Icon name="upload" size={13} />
              Add images
            </button>
            <input accept="image/png,image/jpeg,image/webp" multiple onChange={addFiles} ref={fileRef} type="file" />
            {profile?.supports_masks ? (
              <>
                <button onClick={() => maskRef.current?.click()} type="button">
                  <Icon name="edit" size={13} />
                  {mask ? mask.name : "Add mask"}
                </button>
                <input accept="image/png,image/jpeg,image/webp" onChange={(event) => { setMask(event.target.files?.[0] ?? null); event.target.value = ""; }} ref={maskRef} type="file" />
              </>
            ) : null}
            <button onClick={() => setAdvanced((value) => !value)} type="button">
              <Icon name="settings" size={13} />
              Parameters
            </button>
            <button className={styles.submit} disabled={!prompt.trim() || !capable || working} type="submit">
              {working ? "Working…" : editing ? "Edit" : "Generate"}
            </button>
          </div>

          {advanced ? (
            <div className={styles.parameters}>
              <label>Size<input onChange={(event) => setSize(event.target.value)} placeholder={profile?.default_size ?? "provider default"} value={size} /></label>
              <label>Quality<input onChange={(event) => setQuality(event.target.value)} placeholder={profile?.default_quality ?? "provider default"} value={quality} /></label>
              <label>Format<select onChange={(event) => setFormat(event.target.value as typeof format)} value={format}><option value="">Profile default</option><option value="png">PNG</option><option value="jpeg">JPEG</option><option value="webp">WebP</option></select></label>
              <label>Count<input max={4} min={1} onChange={(event) => setCount(Number(event.target.value))} type="number" value={count} /></label>
              <label>Background<input onChange={(event) => setBackground(event.target.value)} placeholder={profile?.default_background ?? "provider default"} value={background} /></label>
              <label>Input fidelity<input onChange={(event) => setInputFidelity(event.target.value)} placeholder={profile?.default_input_fidelity ?? "provider default"} value={inputFidelity} /></label>
              <label className={styles.providerJson}>Additional provider parameters<textarea onChange={(event) => setProviderParameters(event.target.value)} rows={4} value={providerParameters} /></label>
            </div>
          ) : null}
        </form>
      ) : null}
    </div>
  );
}

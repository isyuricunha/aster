import type { Metadata } from "next";

import type { ConversationSummary, ModelPreferences } from "../../lib/api";
import type { ImageGallery, ImageModelProfile } from "../../lib/image-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { ImageWorkspace } from "./image-workspace";

export const metadata: Metadata = { title: "Images" };

export const dynamic = "force-dynamic";

type InitialImages = {
  gallery: ImageGallery;
  profiles: ImageModelProfile[];
  preferences: ModelPreferences | null;
  conversations: ConversationSummary[];
  error: string | null;
};

async function getInitialImages(): Promise<InitialImages> {
  try {
    const responses = await Promise.all([
      serverApiFetch("/api/image-gallery?limit=100"),
      serverApiFetch("/api/image-model-profiles"),
      serverApiFetch("/api/model-preferences"),
      serverApiFetch("/api/conversations"),
    ]);
    if (responses.some((response) => !response.ok)) {
      throw new Error("The image API returned an error.");
    }
    const [gallery, profiles, preferences, conversations] = await Promise.all(
      responses.map((response) => response.json()),
    );
    return {
      gallery: gallery as ImageGallery,
      profiles: profiles as ImageModelProfile[],
      preferences: preferences as ModelPreferences,
      conversations: conversations as ConversationSummary[],
      error: null,
    };
  } catch (error) {
    return {
      gallery: { items: [], total: 0, offset: 0, limit: 100 },
      profiles: [],
      preferences: null,
      conversations: [],
      error: error instanceof Error ? error.message : "Could not load images.",
    };
  }
}

export default async function ImagesPage() {
  await requireServerAuth();
  const initial = await getInitialImages();
  return (
    <AppFrame
      active="images"
      kicker="Visual workspace"
      title="Images"
      description="Review private image history and declare provider-specific generation and editing capabilities."
    >
      <ImageWorkspace
        initialGallery={initial.gallery}
        initialProfiles={initial.profiles}
        initialPreferences={initial.preferences}
        conversations={initial.conversations}
        initialError={initial.error}
      />
    </AppFrame>
  );
}

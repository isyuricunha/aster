import { redirect } from "next/navigation";

import { requireServerAuth } from "../../lib/server-api";

export default async function DiscordPage() {
  await requireServerAuth();
  redirect("/connections");
}

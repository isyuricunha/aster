import Link from "next/link";

import { AsterMark, Icon } from "./ui/icons";

export default function NotFound() {
  return (
    <main className="route-state">
      <AsterMark size={32} />
      <div>
        <p>Workspace view not found</p>
        <span>The requested Aster page does not exist or is no longer available.</span>
      </div>
      <Link className="button button-secondary" href="/">
        <Icon name="chat" size={14} />
        Return to chat
      </Link>
    </main>
  );
}

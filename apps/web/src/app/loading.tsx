import { AsterMark } from "./ui/icons";

export default function Loading() {
  return (
    <main aria-busy="true" aria-live="polite" className="route-state" role="status">
      <AsterMark size={32} />
      <div>
        <p>Loading workspace</p>
        <span>Preparing your private Aster view.</span>
      </div>
    </main>
  );
}

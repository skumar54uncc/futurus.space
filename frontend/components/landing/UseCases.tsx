import Link from "next/link";

const cases = [
  {
    tag: "Startup",
    question: "Will people pay $29/month for this?",
    insight: "Pricing · Adoption · Churn risk",
    starter:
      "I'm working on a startup and need to know: would people realistically pay around $29/month for this product? Describe the core value in one paragraph.",
  },
  {
    tag: "Creative",
    question: "Would this film concept find an audience?",
    insight: "Audience reach · Viral spread",
    starter:
      "I have a film / creative project idea and want to understand whether a real audience would show up and how word might spread.",
  },
  {
    tag: "Local Business",
    question: "Should I open a coffee shop here?",
    insight: "Foot traffic · Segment fit",
    starter:
      "I'm thinking of opening a local business (like a coffee shop) in my area and want to simulate how nearby customers might react.",
  },
  {
    tag: "Side Project",
    question: "Will my YouTube channel grow?",
    insight: "Growth rate · Retention · Pivots",
    starter:
      "I have a side project (e.g. a YouTube channel or small product) and want to see how growth and retention might play out.",
  },
  {
    tag: "Community",
    question: "How will my neighbourhood react to this?",
    insight: "Support · Opposition · Spread",
    starter:
      "I want to propose a community or neighbourhood initiative and understand how different residents might respond.",
  },
  {
    tag: "Fiction",
    question: "How would readers react if my character dies?",
    insight: "Emotional response · Loyalty",
    starter:
      "I'm writing fiction and considering a bold plot turn (e.g. a main character dies). How might readers react emotionally and would they keep reading?",
  },
];

export function UseCases() {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="max-w-5xl mx-auto px-4">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] text-[11px] text-slate-500 uppercase tracking-widest mb-6">
            Use cases
          </div>
          <h2 className="text-3xl sm:text-4xl font-serif italic text-white mb-4">
            For every kind of idea
          </h2>
          <p className="text-slate-500 text-sm max-w-xs mx-auto">
            Not just startups. Any idea. Any person.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {cases.map((c) => (
            <Link
              key={c.tag}
              href={`/new?idea=${encodeURIComponent(c.starter)}`}
              className="group glass rounded-2xl p-6 flex flex-col gap-3 transition-all duration-200 hover:border-indigo-500/25 hover:-translate-y-0.5 hover:shadow-[0_8px_32px_rgba(99,102,241,0.12)] cursor-pointer block"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-indigo-500 uppercase tracking-[0.12em] px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20">
                  {c.tag}
                </span>
                <span className="text-slate-700 text-sm group-hover:text-indigo-400 transition-colors">&#8594;</span>
              </div>
              <p className="text-sm font-medium text-white leading-snug">
                &ldquo;{c.question}&rdquo;
              </p>
              <p className="text-xs text-slate-600 mt-auto">{c.insight}</p>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

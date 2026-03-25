import Link from "next/link";

const cases = [
  {
    icon: "🚀",
    label: "Startup idea",
    question: "Will people pay $29/month for this?",
    starter:
      "I'm working on a startup and need to know: would people realistically pay around $29/month for this product? Describe the core value in one paragraph.",
  },
  {
    icon: "🎬",
    label: "Creative project",
    question: "Would this film concept find an audience?",
    starter:
      "I have a film / creative project idea and want to understand whether a real audience would show up and how word might spread.",
  },
  {
    icon: "📍",
    label: "Local business",
    question: "Should I open a coffee shop here?",
    starter:
      "I'm thinking of opening a local business (like a coffee shop) in my area and want to simulate how nearby customers might react.",
  },
  {
    icon: "📚",
    label: "Side project",
    question: "Will my YouTube channel grow?",
    starter:
      "I have a side project (e.g. a YouTube channel or small product) and want to see how growth and retention might play out.",
  },
  {
    icon: "🏙️",
    label: "Community idea",
    question: "How will my neighbourhood react to this?",
    starter:
      "I want to propose a community or neighbourhood initiative and understand how different residents might respond.",
  },
  {
    icon: "✍️",
    label: "Novel ending",
    question: "How would readers react if my character dies?",
    starter:
      "I'm writing fiction and considering a bold plot turn (e.g. a main character dies). How might readers react emotionally and would they keep reading?",
  },
];

export function UseCases() {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="max-w-5xl mx-auto px-4">
        <h2 className="text-3xl font-serif italic text-center text-white mb-4">
          For every kind of idea
        </h2>
        <p className="text-center text-slate-500 mb-16">
          Not just startups. Any idea. Any person.
        </p>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {cases.map((c) => (
            <div
              key={c.label}
              className="glass glass-hover rounded-xl p-6 transition-all duration-300 group"
            >
              <div className="text-2xl mb-3">{c.icon}</div>
              <div className="text-sm font-medium text-white mb-1.5">{c.label}</div>
              <p className="text-sm text-slate-400 italic">&ldquo;{c.question}&rdquo;</p>
              <Link
                href={`/new?idea=${encodeURIComponent(c.starter)}`}
                className="mt-4 inline-flex items-center text-xs font-medium text-indigo-400 hover:text-indigo-300 underline-offset-2 hover:underline"
              >
                simulate this &rarr;
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

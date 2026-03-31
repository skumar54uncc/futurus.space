import { Logo } from "@/components/ui/Logo";
import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-white/[0.06] py-16 mt-20">
      <div className="max-w-5xl mx-auto px-4">
        <div className="flex flex-col md:flex-row items-start justify-between gap-10 flex-wrap">
          <div className="max-w-[280px]">
            <Logo size="md" />
            <p className="text-sm text-slate-500 mt-3 leading-relaxed">
              See what is about to be. Multi-agent simulation for anyone with an idea worth testing.
            </p>
            <p className="text-xs text-slate-400 mt-3 italic">
              From Latin <em>futurus</em>: that which is about to be.
            </p>
          </div>

          <div className="flex gap-12 flex-wrap">
            <div>
              <h4 className="text-xs font-medium text-slate-500 uppercase tracking-widest mb-4">
                Product
              </h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link
                    href="/#how-it-works"
                    className="text-slate-500 hover:text-white transition-colors duration-150"
                  >
                    How it works
                  </Link>
                </li>
                <li>
                  <Link
                    href="/sign-up"
                    className="text-slate-500 hover:text-white transition-colors duration-150"
                  >
                    Get started
                  </Link>
                </li>
                <li>
                  <Link
                    href="/#faq"
                    className="text-slate-500 hover:text-white transition-colors duration-150"
                  >
                    FAQ
                  </Link>
                </li>
                <li>
                  <Link
                    href="/contact"
                    className="text-slate-500 hover:text-white transition-colors duration-150"
                  >
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-medium text-slate-500 uppercase tracking-widest mb-4">
                Legal
              </h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link
                    href="/privacy"
                    className="text-slate-500 hover:text-white transition-colors duration-150"
                  >
                    Privacy
                  </Link>
                </li>
                <li>
                  <Link
                    href="/terms"
                    className="text-slate-500 hover:text-white transition-colors duration-150"
                  >
                    Terms
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-white/[0.04] flex flex-col sm:flex-row items-center justify-between gap-4 flex-wrap">
          <p className="text-xs text-slate-600">
            © {new Date().getFullYear()} Futurus · Built by{" "}
            <a
              href="https://www.linkedin.com/in/shailesh-entrant/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Shailesh Kumar
            </a>
          </p>
          <p className="font-serif italic text-xs text-slate-400 text-center sm:text-right">
            futurus — Latin: that which is about to be
          </p>
        </div>
      </div>
    </footer>
  );
}

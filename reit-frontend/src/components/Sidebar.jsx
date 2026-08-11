import { useState } from "react";
import {
  Menu,
  X,
  LayoutDashboard,
  LineChart,
  MessageCircle,
  Heart,
  Trash2,
  LogOut,
} from "lucide-react";
import GoogleLoginButton from "./GoogleLoginButton";

const NAV_ITEMS = [
  { href: "#browse", label: "Browse", icon: LayoutDashboard },
  { href: "#chart", label: "Price History", icon: LineChart },
  { href: "#assistant", label: "Assistant", icon: MessageCircle },
];

function Sidebar({ favourites, onSelectFavourite, onRemoveFavourite, user, onLoginCredential, onLogout }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={`fixed top-4 left-4 z-50 w-10 h-10 rounded-full bg-white/80 dark:bg-slate-800/80 backdrop-blur flex items-center justify-center hover:bg-slate-100 dark:hover:bg-slate-700 shadow-lg text-slate-700 dark:text-slate-200 transition-opacity ${
          open ? "opacity-0 pointer-events-none" : "opacity-100"
        }`}
        aria-label="Open navigation"
      >
        <Menu className="w-5 h-5" />
      </button>

      <nav
        className={`fixed top-4 left-4 z-40 w-72 max-h-[calc(100vh-2rem)] overflow-y-auto rounded-2xl bg-white/95 dark:bg-slate-900/95 backdrop-blur-lg border border-slate-200 dark:border-slate-700/50 shadow-2xl p-5 transition-all duration-300 origin-top-left ${
          open
            ? "opacity-100 scale-100 translate-x-0"
            : "opacity-0 scale-95 -translate-x-4 pointer-events-none"
        }`}
        aria-label="Main navigation"
      >
        <button
          onClick={() => setOpen(false)}
          className="absolute top-3 right-3 w-7 h-7 flex items-center justify-center rounded text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
          aria-label="Close navigation"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="mt-6 pb-4 border-b border-slate-200 dark:border-slate-700/50">
          {user ? (
            <div className="flex items-center justify-between px-1">
              <div className="min-w-0">
                <p className="text-slate-800 dark:text-slate-200 text-sm font-medium truncate">{user.name || user.email}</p>
                <p className="text-slate-500 text-xs truncate">{user.email}</p>
              </div>
              <button
                onClick={onLogout}
                className="text-slate-500 hover:text-red-400 transition p-1.5 shrink-0"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <GoogleLoginButton onCredential={onLoginCredential} />
          )}
        </div>

        <ul className="space-y-2 mt-6">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
            <li key={href}>
              <a
                href={href}
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </a>
            </li>
          ))}
        </ul>

        <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700/50">
          <div className="flex items-center gap-2 px-3 mb-2 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wide">
            <Heart className="w-3.5 h-3.5" />
            <span>Favourites</span>
          </div>

          {!user ? (
            <p className="px-3 text-sm text-slate-500">Sign in to save favourites.</p>
          ) : favourites.length === 0 ? (
            <p className="px-3 text-sm text-slate-500">
              No favourites yet — tap the heart on a ticker to save it.
            </p>
          ) : (
            <ul className="space-y-1">
              {favourites.map((f) => (
                <li
                  key={f.ticker}
                  className="flex items-center justify-between px-3 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 group"
                >
                  <button
                    onClick={() => {
                      onSelectFavourite(f.ticker);
                      setOpen(false);
                    }}
                    className="flex-1 text-left"
                  >
                    <span className="text-slate-800 dark:text-slate-200 font-medium">
                      {f.ticker}
                    </span>
                    {f.name && (
                      <span className="block text-xs text-slate-500 truncate">
                        {f.name}
                      </span>
                    )}
                  </button>
                  <button
                    onClick={() => onRemoveFavourite(f.ticker)}
                    className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition"
                    aria-label={`Remove ${f.ticker} from favourites`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </nav>

      {open && (
        <div
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-30 bg-black/30"
          aria-hidden="true"
        />
      )}
    </>
  );
}

export default Sidebar;

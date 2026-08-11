import { useEffect, useState } from "react";
import {
  getCategories,
  getEtfs,
  getStocks,
  getPriceHistory,
  getFavourites,
  addFavourite,
  removeFavourite,
} from "./api";
import { useScrollReveal } from "./hooks/useScrollReveal";
import { useAuth } from "./hooks/useAuth";
import { useTheme } from "./hooks/useTheme";
import Sidebar from "./components/Sidebar";
import ThemeToggle from "./components/ThemeToggle";
import AnimatedChartBackground from "./components/AnimatedChartBackground";
import Filters from "./components/Filters";
import TickerList from "./components/TickerList";
import PriceChart from "./components/PriceChart";
import AssistantChat from "./components/AssistantChat";
import FavouriteInsights from "./components/FavouriteInsights";

const REVEAL_CLASSES = "transition-all duration-700 ease-out";
function revealClass(visible) {
  return `${REVEAL_CLASSES} ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`;
}

function App() {
  const [assetType, setAssetType] = useState("etfs");
  const [categories, setCategories] = useState({
    etf_categories: [],
    stock_sectors: [],
  });
  const [selectedFilter, setSelectedFilter] = useState("");

  const [items, setItems] = useState([]);
  const [itemsLoading, setItemsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const [selectedTicker, setSelectedTicker] = useState(null);
  const [priceHistory, setPriceHistory] = useState([]);
  const [priceLoading, setPriceLoading] = useState(false);
  const [priceError, setPriceError] = useState(false);

  const [favourites, setFavourites] = useState([]);
  const { user, ready: authReady, login, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    getCategories()
      .then(setCategories)
      .catch(() => setCategories({ etf_categories: [], stock_sectors: [] }));
  }, []);

  useEffect(() => {
    if (!authReady || !user) {
      setFavourites([]);
      return;
    }
    getFavourites()
      .then(setFavourites)
      .catch(() => setFavourites([]));
  }, [authReady, user]);

  function isFavourite(ticker) {
    return favourites.some((f) => f.ticker === ticker);
  }

  async function handleToggleFavourite(item) {
    if (!user) {
      alert("Sign in to save favourites.");
      return;
    }
    if (isFavourite(item.ticker)) {
      await removeFavourite(item.ticker);
      setFavourites((prev) => prev.filter((f) => f.ticker !== item.ticker));
    } else {
      const assetTypeSingular = assetType === "etfs" ? "etf" : "stock";
      await addFavourite(item.ticker, assetTypeSingular, item.name);
      setFavourites((prev) => [
        { ticker: item.ticker, asset_type: assetTypeSingular, name: item.name },
        ...prev,
      ]);
    }
  }

  async function handleRemoveFavourite(ticker) {
    await removeFavourite(ticker);
    setFavourites((prev) => prev.filter((f) => f.ticker !== ticker));
  }

  useEffect(() => {
    setItemsLoading(true);
    const fetcher =
      assetType === "etfs"
        ? getEtfs(selectedFilter)
        : getStocks(selectedFilter);
    fetcher
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setItemsLoading(false));
  }, [assetType, selectedFilter]);

  useEffect(() => {
    if (!selectedTicker) return;
    setPriceLoading(true);
    setPriceError(false);
    getPriceHistory(selectedTicker)
      .then((data) => setPriceHistory(data.history))
      .catch(() => setPriceError(true))
      .finally(() => setPriceLoading(false));
  }, [selectedTicker]);

  function handleAssetTypeChange(type) {
    setAssetType(type);
    setSelectedFilter("");
  }

  const categoryOptions =
    assetType === "etfs" ? categories.etf_categories : categories.stock_sectors;

  const filteredItems = searchQuery
    ? items.filter(
        (item) =>
          item.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
          item.name?.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : items;

  const [browseRef, browseVisible] = useScrollReveal();
  const [chartRef, chartVisible] = useScrollReveal();
  const [assistantRef, assistantVisible] = useScrollReveal();

  return (
    <div className="relative min-h-screen text-slate-900 dark:text-white font-sans">
      <div className="fixed inset-0 -z-10 bg-white dark:bg-slate-900">
        <AnimatedChartBackground />
      </div>

      <ThemeToggle theme={theme} onToggle={toggleTheme} />
      <Sidebar
        favourites={favourites}
        onSelectFavourite={setSelectedTicker}
        onRemoveFavourite={handleRemoveFavourite}
        user={user}
        onLoginCredential={login}
        onLogout={logout}
      />

      <main className="relative pl-4 pr-4 md:pl-16 md:pr-16">
        <section
          id="overview"
          className="relative min-h-[50vh] flex items-center justify-center px-6"
        >
          <div className="relative z-10 text-center">
            <h1 className="font-bold text-3xl md:text-4xl">
              Stock & ETF Tracker
            </h1>
            <p className="mt-3 max-w-md mx-auto text-slate-600 dark:text-slate-400">
              Browse by category, chart price history, and ask the AI assistant.
            </p>
          </div>
        </section>

        <section
          id="browse"
          ref={browseRef}
          className={`my-8 max-w-6xl mx-auto ${revealClass(browseVisible)}`}
        >
          <h2 className="font-bold text-2xl mb-4">Browse</h2>
          <Filters
            assetType={assetType}
            onAssetTypeChange={handleAssetTypeChange}
            categories={categoryOptions}
            selectedCategory={selectedFilter}
            onCategoryChange={setSelectedFilter}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
          <TickerList
            items={filteredItems}
            assetType={assetType}
            selectedTicker={selectedTicker}
            onSelect={setSelectedTicker}
            loading={itemsLoading}
            isFavourite={isFavourite}
            onToggleFavourite={handleToggleFavourite}
          />
        </section>

        <section
          id="chart"
          ref={chartRef}
          className={`my-8 max-w-6xl mx-auto ${revealClass(chartVisible)}`}
        >
          <h2 className="font-bold text-2xl mb-4">Price History</h2>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700/50 p-4">
            <PriceChart
              ticker={selectedTicker}
              history={priceHistory}
              loading={priceLoading}
              error={priceError}
              theme={theme}
            />
          </div>
          {selectedTicker && isFavourite(selectedTicker) && (
            <FavouriteInsights ticker={selectedTicker} />
          )}
        </section>

        <section
          id="assistant"
          ref={assistantRef}
          className={`my-8 pb-16 max-w-6xl mx-auto ${revealClass(assistantVisible)}`}
        >
          <h2 className="font-bold text-2xl mb-4">Assistant</h2>
          <AssistantChat selectedTicker={selectedTicker} />
        </section>
      </main>
    </div>
  );
}

export default App;

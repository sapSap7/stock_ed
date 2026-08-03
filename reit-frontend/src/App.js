import React, { useEffect, useState } from "react";

function App() {
  const [etfs, setEtfs] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/etfs")
      .then((response) => response.json())
      .then((data) => {
        setEtfs(data);
        setLoading(false);
      })
      .catch((error) => console.error("Error fetching ETFs:", error));
  }, []);

  if (loading) return <h2>Loading...</h2>;

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-gray-900 via-purple-900 to-gray-800 text-white p-4 sm:p-6 lg:p-8">
      <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-center mb-8">
        REIT ETF Tracker
      </h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {Object.values(etfs).map((etf, index) => (
          <div
            key={index}
            className="bg-white/10 backdrop-blur-md rounded-xl shadow-lg p-6 transition duration-300 ease-in-out hover:scale-105 hover:shadow-2xl hover:bg-white/20"
          >
            <h2 className="text-xl font-bold truncate mb-2">{etf.longName}</h2>
            <div className="space-y-2 text-sm text-gray-300">
              <p>
                <strong className="font-semibold text-gray-100">Symbol:</strong>{" "}
                {etf.symbol}
              </p>
              <p>
                <strong className="font-semibold text-gray-100">
                  Previous Close:
                </strong>{" "}
                {etf.previousClose}
              </p>
              <p>
                <strong className="font-semibold text-gray-100">
                  NAV Price:
                </strong>{" "}
                {etf.navPrice}
              </p>
              <p>
                <strong className="font-semibold text-gray-100">
                  Category:
                </strong>{" "}
                {etf.category}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;

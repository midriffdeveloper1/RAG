import { useCallback, useEffect, useState } from "react";


export function useServerPagination(fetcher, { pageSize = 8, deps = [] } = {}) {
  const [page, setPage] = useState(1);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => setReloadToken((t) => t + 1), []);

  useEffect(() => {
    setPage(1);
  }, deps);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetcher(page, pageSize)
      .then((data) => {
        if (cancelled) return;
        setItems(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages || 1);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load data.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, pageSize, reloadToken, ...deps]);

  const startIndex = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endIndex = Math.min(page * pageSize, total);

  return {
    page,
    setPage,
    items,
    setItems,
    total,
    totalPages,
    startIndex,
    endIndex,
    isLoading,
    error,
    reload,
  };
}

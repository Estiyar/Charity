import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchCatalog, fetchCatalogReferences } from '../api/client'
import { initialFilters } from '../components/Filters'

const PAGE_SIZE = 12
const SEARCH_DELAY_MS = 300

export function useCatalog() {
  const [filters, setFilters] = useState(initialFilters)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(1)
  const [view, setView] = useState('cards')
  const [results, setResults] = useState([])
  const [count, setCount] = useState(0)
  const [pageSize, setPageSize] = useState(PAGE_SIZE)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [references, setReferences] = useState({ cities: [], diagnoses: [] })
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(filters.search.trim()), SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [filters.search])

  const queryParams = useMemo(
    () => ({
      city: filters.city,
      diagnosis: filters.diagnosis,
      status: filters.status,
      end_date_from: filters.end_date_from,
      end_date_to: filters.end_date_to,
      target_amount_min: filters.target_amount_min,
      target_amount_max: filters.target_amount_max,
      age_min: filters.age_min,
      age_max: filters.age_max,
      ordering: filters.ordering,
      search: debouncedSearch,
      page,
      page_size: PAGE_SIZE,
    }),
    [
      filters.city,
      filters.diagnosis,
      filters.status,
      filters.end_date_from,
      filters.end_date_to,
      filters.target_amount_min,
      filters.target_amount_max,
      filters.age_min,
      filters.age_max,
      filters.ordering,
      debouncedSearch,
      page,
    ],
  )

  const changeFilters = useCallback((next) => {
    setFilters(next)
    setPage(1)
  }, [])

  const resetFilters = useCallback(() => {
    setFilters(initialFilters)
    setPage(1)
  }, [])

  const reload = useCallback(() => {
    setReloadKey((value) => value + 1)
  }, [])

  useEffect(() => {
    fetchCatalogReferences()
      .then(setReferences)
      .catch(() => setReferences({ cities: [], diagnoses: [] }))
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetchCatalog(queryParams)
      .then((data) => {
        if (cancelled) return
        setResults(data.results || [])
        setCount(Number(data.count) || 0)
        setPageSize(Number(data.page_size) || PAGE_SIZE)
      })
      .catch((err) => {
        if (cancelled) return
        setResults([])
        setCount(0)
        setError(err.message || 'Не удалось загрузить каталог')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [queryParams, reloadKey])

  const pageCount = useMemo(
    () => Math.max(1, Math.ceil(count / pageSize)),
    [count, pageSize],
  )

  return {
    filters,
    changeFilters,
    resetFilters,
    references,
    page,
    setPage,
    pageCount,
    pageSize,
    view,
    setView,
    results,
    count,
    loading,
    error,
    reload,
  }
}

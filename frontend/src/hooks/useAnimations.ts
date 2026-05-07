import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * 防抖Hook
 * @param value 需要防抖的值
 * @param delay 延迟时间(ms)
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(timer)
  }, [value, delay])

  return debouncedValue
}

/**
 * 节流Hook
 * @param callback 回调函数
 * @param delay 间隔时间(ms)
 */
export function useThrottledCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number = 300
): T {
  const lastRun = useRef<number>(0)

  const throttledCallback = useCallback(
    (...args: Parameters<T>) => {
      const now = Date.now()
      if (now - lastRun.current >= delay) {
        lastRun.current = now
        callback(...args)
      }
    },
    [callback, delay]
  ) as T

  return throttledCallback
}

/**
 * IntersectionObserver Hook - 元素可见性检测
 * 用于懒加载、滚动动画触发等场景
 */
export function useInView(options?: IntersectionObserverInit) {
  const ref = useRef<HTMLDivElement>(null)
  const [isInView, setIsInView] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsInView(true)
        // 一旦进入视口后，停止观察（可选）
        // observer.unobserve(element)
      }
    }, {
      threshold: 0.1,
      ...options,
    })

    observer.observe(element)

    return () => observer.disconnect()
  }, [options])

  return { ref, isInView }
}

/**
 * 滚动位置Hook
 */
export function useScrollPosition() {
  const [scrollPosition, setScrollPosition] = useState(0)
  const [isScrolled, setIsScrolled] = useState(false)
  const [scrollDirection, setScrollDirection] = useState<'up' | 'down'>('up')

  useEffect(() => {
    let lastScrollY = window.scrollY

    const handleScroll = () => {
      const currentScrollY = window.scrollY
      setScrollPosition(currentScrollY)
      setIsScrolled(currentScrollY > 20)
      setScrollDirection(currentScrollY > lastScrollY ? 'down' : 'up')
      lastScrollY = currentScrollY
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return { scrollPosition, isScrolled, scrollDirection }
}

/**
 * 本地存储Hook (类型安全)
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.warn(`[useLocalStorage] Error reading key "${key}":`, error)
      return initialValue
    }
  })

  const setValue = (value: T | ((prev: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      window.localStorage.setItem(key, JSON.stringify(valueToStore))
    } catch (error) {
      console.warn(`[useLocalStorage] Error setting key "${key}":`, error)
    }
  }

  return [storedValue, setValue]
}

/**
 * 复制到剪贴板Hook
 */
export function useCopyToClipboard() {
  const [copiedText, setCopiedText] = useState<string>('')
  const [isCopied, setIsCopied] = useState(false)

  const copy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedText(text)
      setIsCopied(true)
      
      // 2秒后重置状态
      setTimeout(() => {
        setIsCopied(false)
        setCopiedText('')
      }, 2000)
      
      return true
    } catch (error) {
      console.warn('[useCopyToClipboard] 复制失败:', error)
      return false
    }
  }, [])

  return { copiedText, isCopied, copy }
}

/**
 * 媒体查询Hook
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia(query)
    setMatches(mediaQuery.matches)

    const handler = (event: MediaQueryListEvent) => setMatches(event.matches)
    
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [query])

  return matches
}

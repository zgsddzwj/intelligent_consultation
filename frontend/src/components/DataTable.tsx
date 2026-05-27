import React, { useState, useCallback, useMemo } from 'react'
import { Table, Pagination, Input, Space, Button, Empty } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import type { TableProps, TablePaginationConfig } from 'antd/es/table'

interface DataTableProps<T> extends Omit<TableProps<T>, 'pagination' | 'dataSource'> {
  data: T[]
  loading?: boolean
  searchable?: boolean
  searchFields?: (keyof T)[]
  defaultPageSize?: number
  pageSizeOptions?: number[]
  emptyText?: string
  onRefresh?: () => void
}

/**
 * DataTable - 通用数据表格组件
 *
 * 功能：
 * - 内置搜索过滤
 * - 分页控制
 * - 空状态处理
 * - 刷新按钮
 * - 响应式布局
 */
export function DataTable<T extends Record<string, any>>({
  data,
  loading = false,
  searchable = true,
  searchFields = [],
  defaultPageSize = 10,
  pageSizeOptions = [10, 20, 50, 100],
  emptyText = '暂无数据',
  onRefresh,
  columns,
  rowKey = 'id',
  ...tableProps
}: DataTableProps<T>) {
  const [searchText, setSearchText] = useState('')
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: defaultPageSize,
  })

  // 过滤数据
  const filteredData = useMemo(() => {
    if (!searchText || searchFields.length === 0) return data

    const lowerSearch = searchText.toLowerCase()
    return data.filter((item) =>
      searchFields.some((field) => {
        const value = item[field]
        return value !== undefined && String(value).toLowerCase().includes(lowerSearch)
      })
    )
  }, [data, searchText, searchFields])

  // 分页数据
  const paginatedData = useMemo(() => {
    const { current = 1, pageSize = defaultPageSize } = pagination
    const start = (current - 1) * pageSize
    return filteredData.slice(start, start + pageSize)
  }, [filteredData, pagination, defaultPageSize])

  const handleTableChange = useCallback((newPagination: TablePaginationConfig) => {
    setPagination(newPagination)
  }, [])

  const handleSearch = useCallback((value: string) => {
    setSearchText(value)
    setPagination((prev) => ({ ...prev, current: 1 }))
  }, [])

  return (
    <div className="data-table-wrapper">
      {searchable && (
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Input.Search
            placeholder="搜索..."
            allowClear
            enterButton={<SearchOutlined />}
            onSearch={handleSearch}
            onChange={(e) => handleSearch(e.target.value)}
            style={{ maxWidth: 300 }}
            aria-label="搜索表格数据"
          />
          {onRefresh && (
            <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={loading}>
              刷新
            </Button>
          )}
        </div>
      )}

      <Table
        {...tableProps}
        columns={columns}
        dataSource={paginatedData}
        loading={loading}
        rowKey={rowKey}
        pagination={{
          ...pagination,
          total: filteredData.length,
          pageSizeOptions,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        onChange={handleTableChange}
        locale={{ emptyText: <Empty description={emptyText} /> }}
        scroll={{ x: 'max-content' }}
      />
    </div>
  )
}

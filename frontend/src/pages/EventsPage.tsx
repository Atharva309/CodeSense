import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, type EventResponse } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function EventsPage() {
  const [page, setPage] = useState(1)
  const pageSize = 20

  const { data, isLoading, error } = useQuery({
    queryKey: ['events', { page, pageSize }],
    queryFn: () => api.getEvents({ page, pageSize }),
  })

  const getStatusBadgeVariant = (status: string | null) => {
    if (!status) return 'outline'
    switch (status.toLowerCase()) {
      case 'done':
        return 'default'
      case 'running':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Events</h2>
          <p className="text-muted-foreground">All code review events</p>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-destructive">
              Error loading events. Please try again.
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Events</h2>
        <p className="text-muted-foreground">All code review events</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Events</CardTitle>
          <CardDescription>
            Showing {data?.events.length ?? 0} of {data?.total ?? 0} events
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">Loading events...</div>
          ) : data?.events.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No events found
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">ID</th>
                      <th className="text-left p-2">Type</th>
                      <th className="text-left p-2">Repository</th>
                      <th className="text-left p-2">Ref</th>
                      <th className="text-left p-2">SHA</th>
                      <th className="text-left p-2">Review Status</th>
                      <th className="text-left p-2">Created</th>
                      <th className="text-left p-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.events.map((event) => (
                      <tr key={event.id} className="border-b hover:bg-accent/50">
                        <td className="p-2 font-mono text-sm">{event.id}</td>
                        <td className="p-2">
                          <Badge variant="outline">{event.event_type}</Badge>
                        </td>
                        <td className="p-2">
                          <code className="text-sm">{event.repo || '-'}</code>
                        </td>
                        <td className="p-2">
                          <code className="text-sm">{event.ref || '-'}</code>
                        </td>
                        <td className="p-2">
                          <code className="text-xs">
                            {event.after_sha ? event.after_sha.substring(0, 7) : '-'}
                          </code>
                        </td>
                        <td className="p-2">
                          {event.latest_review_status ? (
                            <Link to={`/reviews/${event.latest_review_id}`}>
                              <Badge variant={getStatusBadgeVariant(event.latest_review_status)}>
                                {event.latest_review_status}
                              </Badge>
                            </Link>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                        <td className="p-2 text-sm text-muted-foreground">
                          {new Date(event.created_at).toLocaleString()}
                        </td>
                        <td className="p-2">
                          <Link to={`/events/${event.id}`}>
                            <Button variant="ghost" size="sm">View</Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {data && data.total > pageSize && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    Page {page} of {Math.ceil(data.total / pageSize)}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={!data.has_more}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

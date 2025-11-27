import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function Dashboard() {
  const { data: events, isLoading } = useQuery({
    queryKey: ['events', { page: 1, pageSize: 10 }],
    queryFn: () => api.getEvents({ page: 1, pageSize: 10 }),
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Overview of your code reviews</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Events</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? '...' : events?.total ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Events</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? '...' : events?.events.length ?? 0}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Events</CardTitle>
          <CardDescription>Latest code review events</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div>Loading...</div>
          ) : events?.events.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No events yet
            </div>
          ) : (
            <div className="space-y-2">
              {events?.events.map((event) => (
                <div key={event.id} className="flex items-center justify-between p-2 border rounded">
                  <div>
                    <div className="font-medium">{event.repo}</div>
                    <div className="text-sm text-muted-foreground">{event.event_type}</div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {event.latest_review_status || 'No review'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}


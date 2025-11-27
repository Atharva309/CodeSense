import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Play } from 'lucide-react'

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>()
  const eventId = parseInt(id || '0', 10)
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['event', eventId],
    queryFn: () => api.getEvent(eventId),
    enabled: !!eventId,
  })

  const enqueueMutation = useMutation({
    mutationFn: () => api.enqueueEvent(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event', eventId] })
      queryClient.invalidateQueries({ queryKey: ['events'] })
    },
  })

  if (error) {
    return (
      <div className="space-y-6">
        <Link to="/events">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Events
          </Button>
        </Link>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-destructive">
              Error loading event. Please try again.
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/events">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Events
            </Button>
          </Link>
          <h2 className="text-3xl font-bold tracking-tight mt-2">Event {eventId}</h2>
        </div>
        <Button
          onClick={() => enqueueMutation.mutate()}
          disabled={enqueueMutation.isPending}
        >
          <Play className="h-4 w-4 mr-2" />
          {enqueueMutation.isPending ? 'Enqueuing...' : 'Run Review'}
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-8">Loading event details...</div>
      ) : data ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Event Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Type</div>
                  <div className="mt-1">
                    <Badge variant="outline">{data.event.event_type}</Badge>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Repository</div>
                  <div className="mt-1">
                    <code className="text-sm">{data.event.repo || '-'}</code>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Ref</div>
                  <div className="mt-1">
                    <code className="text-sm">{data.event.ref || '-'}</code>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-muted-foreground">SHA</div>
                  <div className="mt-1">
                    <code className="text-xs">{data.event.after_sha || '-'}</code>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-muted-foreground">Created</div>
                  <div className="mt-1 text-sm">
                    {new Date(data.event.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Reviews</CardTitle>
              <CardDescription>
                {data.reviews.length} review{data.reviews.length !== 1 ? 's' : ''} for this event
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.reviews.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  No reviews yet. Click "Run Review" to start one.
                </div>
              ) : (
                <div className="space-y-2">
                  {data.reviews.map((review) => (
                    <Link
                      key={review.id}
                      to={`/reviews/${review.id}`}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div>
                        <div className="font-medium">Review #{review.id}</div>
                        <div className="text-sm text-muted-foreground">
                          Status: {review.status}
                          {review.started_at && (
                            <> • Started: {new Date(review.started_at).toLocaleString()}</>
                          )}
                          {review.finished_at && (
                            <> • Finished: {new Date(review.finished_at).toLocaleString()}</>
                          )}
                        </div>
                      </div>
                      <Badge variant={review.status === 'done' ? 'default' : 'secondary'}>
                        {review.status}
                      </Badge>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  )
}

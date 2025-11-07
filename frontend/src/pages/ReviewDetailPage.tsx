import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import { api, type FindingResponse } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, FileCode, AlertCircle } from 'lucide-react'
import { useState } from 'react'

export default function ReviewDetailPage() {
  const { id } = useParams<{ id: string }>()
  const reviewId = parseInt(id || '0', 10)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['review', reviewId],
    queryFn: () => api.getReview(reviewId),
    enabled: !!reviewId,
  })

  const getSeverityBadgeVariant = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high':
        return 'high'
      case 'medium':
        return 'medium'
      case 'low':
        return 'low'
      case 'info':
        return 'info'
      default:
        return 'outline'
    }
  }

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
              Error loading review. Please try again.
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="text-center py-8">Loading review details...</div>
      </div>
    )
  }

  if (!data) {
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
            <div className="text-center text-muted-foreground">
              Review not found
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const files = Object.keys(data.findings_by_file)
  const staticFindings = data.findings.filter((f) => f.tool !== 'ai')
  const aiFindings = data.findings.filter((f) => f.tool === 'ai')

  return (
    <div className="space-y-6">
      <div>
        <Link to="/events">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Events
          </Button>
        </Link>
        <div className="mt-4">
          <h2 className="text-3xl font-bold tracking-tight">Review #{reviewId}</h2>
          <p className="text-muted-foreground mt-2">
            Repository: <code>{data.event.repo}</code> @{' '}
            <code>{data.event.after_sha?.substring(0, 7)}</code>
          </p>
          <div className="mt-2">
            <Badge variant={data.review.status === 'done' ? 'default' : 'secondary'}>
              {data.review.status}
            </Badge>
          </div>
        </div>
      </div>

      {data.findings.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <div className="text-2xl mb-2">🎉</div>
              <div className="text-lg font-medium">No findings!</div>
              <div className="text-muted-foreground mt-2">
                This code review found no issues.
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <div className="text-2xl font-bold">{data.findings.length}</div>
                  <div className="text-sm text-muted-foreground">Total Findings</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">{staticFindings.length}</div>
                  <div className="text-sm text-muted-foreground">Static Analysis</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">{aiFindings.length}</div>
                  <div className="text-sm text-muted-foreground">AI Suggestions</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">{files.length}</div>
                  <div className="text-sm text-muted-foreground">Files Reviewed</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue={files[0] || 'overview'} className="w-full">
            <TabsList className="w-full justify-start overflow-x-auto">
              {files.map((file) => (
                <TabsTrigger key={file} value={file} className="flex items-center gap-2">
                  <FileCode className="h-4 w-4" />
                  <span className="truncate max-w-[200px]">{file}</span>
                </TabsTrigger>
              ))}
            </TabsList>

            {files.map((file) => {
              const fileFindings = data.findings_by_file[file] || []
              const fileStaticFindings = fileFindings.filter((f) => f.tool !== 'ai')
              const fileAiFindings = fileFindings.filter((f) => f.tool === 'ai')

              return (
                <TabsContent key={file} value={file} className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <FileCode className="h-5 w-5" />
                        {file}
                      </CardTitle>
                      <CardDescription>
                        {fileFindings.length} finding{fileFindings.length !== 1 ? 's' : ''} in this file
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div>
                          <h4 className="font-semibold mb-3 flex items-center gap-2">
                            <AlertCircle className="h-4 w-4" />
                            Static Analysis ({fileStaticFindings.length})
                          </h4>
                          {fileStaticFindings.length === 0 ? (
                            <div className="text-sm text-muted-foreground">
                              No static analysis findings
                            </div>
                          ) : (
                            <div className="space-y-3">
                              {fileStaticFindings.map((finding) => (
                                <FindingCard key={finding.id} finding={finding} />
                              ))}
                            </div>
                          )}
                        </div>
                        <div>
                          <h4 className="font-semibold mb-3 flex items-center gap-2">
                            <AlertCircle className="h-4 w-4" />
                            AI Suggestions ({fileAiFindings.length})
                          </h4>
                          {fileAiFindings.length === 0 ? (
                            <div className="text-sm text-muted-foreground">
                              No AI suggestions
                            </div>
                          ) : (
                            <div className="space-y-3">
                              {fileAiFindings.map((finding) => (
                                <FindingCard key={finding.id} finding={finding} />
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              )
            })}
          </Tabs>
        </>
      )}
    </div>
  )
}

function FindingCard({ finding }: { finding: FindingResponse }) {
  const [showPatch, setShowPatch] = useState(false)

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <Badge variant={getSeverityBadgeVariant(finding.severity)}>
            {finding.severity}
          </Badge>
          {finding.start_line && (
            <span className="text-xs text-muted-foreground">
              Line {finding.start_line}
              {finding.end_line && finding.end_line !== finding.start_line
                ? `-${finding.end_line}`
                : ''}
            </span>
          )}
        </div>
        <h5 className="font-semibold mb-2">{finding.title}</h5>
        {finding.rationale && (
          <p className="text-sm text-muted-foreground mb-3 whitespace-pre-wrap">
            {finding.rationale}
          </p>
        )}
        {finding.patch && (
          <div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowPatch(!showPatch)}
              className="mb-2"
            >
              {showPatch ? 'Hide' : 'Show'} Patch
            </Button>
            {showPatch && (
              <div className="rounded-md overflow-hidden border">
                <SyntaxHighlighter
                  language="diff"
                  style={vscDarkPlus}
                  customStyle={{ margin: 0, borderRadius: 0 }}
                >
                  {finding.patch}
                </SyntaxHighlighter>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function getSeverityBadgeVariant(severity: string) {
  switch (severity.toLowerCase()) {
    case 'high':
      return 'high'
    case 'medium':
      return 'medium'
    case 'low':
      return 'low'
    case 'info':
      return 'info'
    default:
      return 'outline'
  }
}

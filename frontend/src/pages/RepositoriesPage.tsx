import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, Copy, Trash2, Check } from 'lucide-react'
import type { RepositoryResponse } from '@/lib/api'

export default function RepositoriesPage() {
  const [showAddForm, setShowAddForm] = useState(false)
  const [repoName, setRepoName] = useState('')
  const [githubToken, setGithubToken] = useState('')
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const queryClient = useQueryClient()

  const { data: repositories, isLoading } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => api.getRepositories(),
  })

  const createMutation = useMutation({
    mutationFn: (request: { repo_full_name: string; github_token?: string }) =>
      api.createRepository(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      setShowAddForm(false)
      setRepoName('')
      setGithubToken('')
    },
  })

  const disconnectMutation = useMutation({
    mutationFn: (repoId: number) => api.disconnectRepository(repoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
    },
  })

  const handleCopy = (repo: RepositoryResponse) => {
    navigator.clipboard.writeText(repo.webhook_url)
    setCopiedId(repo.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!repoName.trim()) return

    createMutation.mutate({
      repo_full_name: repoName.trim(),
      github_token: githubToken.trim() || undefined,
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Repositories</h2>
          <p className="text-muted-foreground">Manage your connected GitHub repositories</p>
        </div>
        <Button onClick={() => setShowAddForm(!showAddForm)}>
          <Plus className="h-4 w-4 mr-2" />
          Connect Repository
        </Button>
      </div>

      {showAddForm && (
        <Card>
          <CardHeader>
            <CardTitle>Connect New Repository</CardTitle>
            <CardDescription>
              Enter your repository name in the format: username/repo-name
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="repo-name" className="block text-sm font-medium mb-1">
                  Repository Name
                </label>
                <input
                  id="repo-name"
                  type="text"
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  placeholder="username/repo-name"
                  required
                  className="w-full px-3 py-2 border rounded-md bg-background"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  Example: octocat/Hello-World
                </p>
              </div>
              <div>
                <label htmlFor="github-token" className="block text-sm font-medium mb-1">
                  GitHub Token (Optional)
                </label>
                <input
                  id="github-token"
                  type="password"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxx"
                  className="w-full px-3 py-2 border rounded-md bg-background"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  Required for private repositories
                </p>
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Connecting...' : 'Connect'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowAddForm(false)
                    setRepoName('')
                    setGithubToken('')
                  }}
                >
                  Cancel
                </Button>
              </div>
              {createMutation.isError && (
                <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
                  {createMutation.error instanceof Error
                    ? createMutation.error.message
                    : 'Failed to connect repository'}
                </div>
              )}
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Connected Repositories</CardTitle>
          <CardDescription>
            {repositories?.length || 0} repository{repositories?.length !== 1 ? 'ies' : ''} connected
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">Loading repositories...</div>
          ) : repositories?.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">No repositories connected yet</p>
              <Button onClick={() => setShowAddForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Connect Your First Repository
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {repositories?.map((repo) => (
                <Card key={repo.id}>
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold">{repo.repo_full_name}</h3>
                          <Badge variant={repo.is_active ? 'default' : 'secondary'}>
                            {repo.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        <div className="space-y-2">
                          <div>
                            <label className="text-sm font-medium text-muted-foreground">
                              Webhook URL:
                            </label>
                            <div className="flex items-center gap-2 mt-1">
                              <code className="flex-1 px-3 py-2 bg-muted rounded-md text-sm break-all">
                                {repo.webhook_url}
                              </code>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleCopy(repo)}
                              >
                                {copiedId === repo.id ? (
                                  <Check className="h-4 w-4" />
                                ) : (
                                  <Copy className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Copy this URL and add it to your GitHub repository webhook settings
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          if (confirm(`Disconnect ${repo.repo_full_name}?`)) {
                            disconnectMutation.mutate(repo.id)
                          }
                        }}
                        disabled={disconnectMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}


import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/api";
import { useState } from "react";
import { Hash, MapPin, Mail, Plus, X, Edit } from "lucide-react";
import type { Hashtag, Location, DMTemplate } from "@shared/schema";

export default function Content() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [hashtagInput, setHashtagInput] = useState("");
  const [hashtagTier, setHashtagTier] = useState(2);
  const [locationInput, setLocationInput] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [templateText, setTemplateText] = useState("");

  const { data: hashtags } = useQuery<Hashtag[]>({
    queryKey: ["/api/hashtags"],
  });

  const { data: locations } = useQuery<Location[]>({
    queryKey: ["/api/locations"],
  });

  const { data: dmTemplates } = useQuery<DMTemplate[]>({
    queryKey: ["/api/dm-templates"],
  });

  const addHashtagMutation = useMutation({
    mutationFn: async (data: { tag: string; tier: number }) => {
      return await apiRequest("POST", "/api/hashtags", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/hashtags"] });
      setHashtagInput("");
      setHashtagTier(2);
      toast({
        title: "Success",
        description: "Hashtag added successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const removeHashtagMutation = useMutation({
    mutationFn: async (id: string) => {
      return await apiRequest("DELETE", `/api/hashtags/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/hashtags"] });
      toast({
        title: "Success",
        description: "Hashtag removed successfully",
      });
    },
  });

  const addLocationMutation = useMutation({
    mutationFn: async (data: { name: string; instagram_pk: string }) => {
      return await apiRequest("POST", "/api/locations", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/locations"] });
      setLocationInput("");
      toast({
        title: "Success",
        description: "Location added successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const removeLocationMutation = useMutation({
    mutationFn: async (id: string) => {
      return await apiRequest("DELETE", `/api/locations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/locations"] });
      toast({
        title: "Success",
        description: "Location removed successfully",
      });
    },
  });

  const addTemplateMutation = useMutation({
    mutationFn: async (data: { name: string; template: string }) => {
      return await apiRequest("POST", "/api/dm-templates", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/dm-templates"] });
      setTemplateName("");
      setTemplateText("");
      toast({
        title: "Success",
        description: "DM template added successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const removeTemplateMutation = useMutation({
    mutationFn: async (id: string) => {
      return await apiRequest("DELETE", `/api/dm-templates/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/dm-templates"] });
      toast({
        title: "Success",
        description: "DM template removed successfully",
      });
    },
  });

  const handleAddHashtag = () => {
    if (!hashtagInput.trim()) {
      toast({
        title: "Error",
        description: "Please enter a hashtag",
        variant: "destructive",
      });
      return;
    }

    addHashtagMutation.mutate({
      tag: hashtagInput.replace("#", "").trim(),
      tier: hashtagTier,
    });
  };

  const handleAddLocation = () => {
    if (!locationInput.trim()) {
      toast({
        title: "Error",
        description: "Please enter a location",
        variant: "destructive",
      });
      return;
    }

    // For demo purposes, we'll use a placeholder Instagram PK
    // In real implementation, this would search Instagram's location API
    addLocationMutation.mutate({
      name: locationInput.trim(),
      instagram_pk: Math.random().toString().substring(2, 12), // Placeholder PK
    });
  };

  const handleAddTemplate = () => {
    if (!templateName.trim() || !templateText.trim()) {
      toast({
        title: "Error",
        description: "Please fill in both template name and text",
        variant: "destructive",
      });
      return;
    }

    addTemplateMutation.mutate({
      name: templateName.trim(),
      template: templateText.trim(),
    });
  };

  return (
    <div className="p-6 space-y-6" data-testid="content-content">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hashtags Management */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Hash className="h-5 w-5" />
              <span>Hashtags Management</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex space-x-2">
                <div className="flex-1">
                  <Input
                    placeholder="Add hashtag (without #)"
                    value={hashtagInput}
                    onChange={(e) => setHashtagInput(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && handleAddHashtag()}
                    data-testid="input-hashtag"
                  />
                </div>
                <div className="w-20">
                  <Input
                    type="number"
                    min="1"
                    max="5"
                    value={hashtagTier}
                    onChange={(e) => setHashtagTier(parseInt(e.target.value) || 2)}
                    placeholder="Tier"
                    data-testid="input-hashtag-tier"
                  />
                </div>
                <Button 
                  onClick={handleAddHashtag}
                  disabled={addHashtagMutation.isPending}
                  data-testid="button-add-hashtag"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground">Current Hashtags</h3>
                <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
                  {hashtags?.map((hashtag) => (
                    <Badge key={hashtag.id} variant="secondary" className="flex items-center space-x-2">
                      <span>#{hashtag.tag}</span>
                      <span className="text-xs opacity-70">T{hashtag.tier}</span>
                      <button
                        onClick={() => removeHashtagMutation.mutate(hashtag.id)}
                        className="text-destructive hover:text-destructive/80 ml-1"
                        data-testid={`button-remove-hashtag-${hashtag.id}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                  
                  {(!hashtags || hashtags.length === 0) && (
                    <p className="text-sm text-muted-foreground">No hashtags configured</p>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Locations Management */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MapPin className="h-5 w-5" />
              <span>Locations Management</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex space-x-2">
                <Input
                  placeholder="Search and add location"
                  value={locationInput}
                  onChange={(e) => setLocationInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleAddLocation()}
                  className="flex-1"
                  data-testid="input-location"
                />
                <Button 
                  onClick={handleAddLocation}
                  disabled={addLocationMutation.isPending}
                  data-testid="button-add-location"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground">Current Locations</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {locations?.map((location) => (
                    <div key={location.id} className="flex items-center justify-between p-2 bg-muted rounded-lg">
                      <div className="flex items-center space-x-2">
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{location.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeLocationMutation.mutate(location.id)}
                        data-testid={`button-remove-location-${location.id}`}
                      >
                        <X className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  ))}
                  
                  {(!locations || locations.length === 0) && (
                    <p className="text-sm text-muted-foreground">No locations configured</p>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* DM Templates */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Mail className="h-5 w-5" />
            <span>DM Templates</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Add New Template */}
            <div className="space-y-4 p-4 border border-border rounded-lg">
              <h3 className="font-medium">Add New Template</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="template-name">Template Name</Label>
                  <Input
                    id="template-name"
                    placeholder="Welcome Message"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    data-testid="input-template-name"
                  />
                </div>
                <div className="md:col-span-1">
                  <Label htmlFor="template-text">Template Text</Label>
                  <Textarea
                    id="template-text"
                    placeholder="Hey {username}! Thanks for following..."
                    value={templateText}
                    onChange={(e) => setTemplateText(e.target.value)}
                    rows={3}
                    data-testid="textarea-template"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Use {"{username}"} for personalization
                  </p>
                </div>
              </div>
              <Button 
                onClick={handleAddTemplate}
                disabled={addTemplateMutation.isPending}
                data-testid="button-add-template"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Template
              </Button>
            </div>

            {/* Existing Templates */}
            <div className="space-y-4">
              <h3 className="font-medium">Existing Templates</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {dmTemplates?.map((template) => (
                  <div key={template.id} className="p-4 bg-muted rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium">{template.name}</h4>
                      <div className="flex space-x-2">
                        <Button variant="ghost" size="sm" data-testid={`button-edit-template-${template.id}`}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeTemplateMutation.mutate(template.id)}
                          data-testid={`button-remove-template-${template.id}`}
                        >
                          <X className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2 line-clamp-3">
                      {template.template}
                    </p>
                    <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                      <span>Used: {template.usage_count} times</span>
                      <span>•</span>
                      <span>Success: {template.success_rate}%</span>
                    </div>
                  </div>
                ))}
                
                {(!dmTemplates || dmTemplates.length === 0) && (
                  <div className="col-span-2 text-center py-8 text-muted-foreground">
                    <Mail className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>No DM templates configured</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

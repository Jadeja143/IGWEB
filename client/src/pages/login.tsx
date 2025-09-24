import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const { toast } = useToast();
  const [, setLocation] = useLocation();
  const { checkAuth } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Fetch CSRF token first
      const csrfResponse = await fetch("/api/csrf-token", {
        credentials: "include",
      });
      const csrfData = await csrfResponse.json();
      
      if (!csrfData.success) {
        throw new Error("Failed to get CSRF token");
      }

      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfData.csrf_token,
        },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (data.success) {
        toast({
          title: "Login successful",
          description: "Welcome to the Instagram Bot Management Dashboard",
        });
        // Refresh authentication state
        await checkAuth();
        setLocation("/");
      } else {
        toast({
          title: "Login failed",
          description: data.message || "Invalid username or password",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Login error",
        description: "Unable to connect to the server",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Fetch CSRF token first
      const csrfResponse = await fetch("/api/csrf-token", {
        credentials: "include",
      });
      const csrfData = await csrfResponse.json();
      
      if (!csrfData.success) {
        throw new Error("Failed to get CSRF token");
      }

      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfData.csrf_token,
        },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (data.success) {
        toast({
          title: "Registration successful",
          description: "Account created and logged in successfully",
        });
        // Refresh authentication state
        await checkAuth();
        setLocation("/");
      } else {
        toast({
          title: "Registration failed",
          description: data.message || "Unable to create account",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Registration error",
        description: "Unable to connect to the server",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl text-center">Instagram Bot Dashboard</CardTitle>
          <CardDescription className="text-center">
            {showRegister ? "Create your account" : "Sign in to your account"}
          </CardDescription>
        </CardHeader>
        <form onSubmit={showRegister ? handleRegister : handleLogin}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Loading..." : showRegister ? "Create Account" : "Sign In"}
            </Button>
            <div className="text-center">
              <button
                type="button"
                className="text-sm text-blue-600 hover:text-blue-500"
                onClick={() => setShowRegister(!showRegister)}
              >
                {showRegister ? "Already have an account? Sign in" : "Don't have an account? Register"}
              </button>
            </div>
            {!showRegister && (
              <div className="text-xs text-gray-500 text-center">
                Demo credentials: admin / password
              </div>
            )}
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
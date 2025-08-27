# discuitStuff
So I have written a few scripts in Python that basically get feeds from Cricket Websites (RapidAPI and CricBuzz API and RSS) and automatically post them to Discuit in the d/Cricket forum. This below is written in BASH with cURL for clarity, but is just as simple in Powershell (allegedly). I am assuming Linux as that is what I know, but if anyone wants to write a Windows version I will help as much as I can.

A warning. If you have never done API calls before the following is gibberish, trust me. If you have done API calls then it will be as clear as mud. Knowledge of jq helps. It took me the best part of a week to get it working.

So the first part of the trick is getting the initial login right.

To start with you will need to get a CSRF Token. CSRF is Cross Site Request Forgery protection and is a security mechanism that ensures requests are coming from legitimate sources. 

So first you need to make a request to get the token

```
DISCUIT_BASE="https://discuit.org"

curl -s -c /tmp/cookies.txt "$DISCUIT_BASE/api/_initial" > /tmp/discuit_initial.json
csrf_token=$(curl -s -b /tmp/cookies.txt -D /tmp/headers.txt "$DISCUIT_BASE/api/_initial" | jq -r 'empty')
csrf_token=$(grep -i "csrf-token:" /tmp/headers.txt | cut -d' ' -f2 | tr -d '\r')
```

if you 'echo $csrf_token' you should have one and also /tmp will have text files

First, the script calls /api/_initial endpoint and endpoint returns a CSRF token in the HTTP response headers (specifically in the csrf-token header). The script also saves any session cookies from this initial request for later use in /tmp/cookies.txt

Once you have that you can do an Authentication request
```
login_response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
    -b /tmp/cookies.txt -c /tmp/cookies.txt \
    -H "Content-Type: application/json" \
    -H "X-Csrf-Token: $csrf_token" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
    "$DISCUIT_BASE/api/_login")
```
This makes a POST request to /api/_login with:
Existing cookies from the initial request (session context)
CSRF token in the X-Csrf-Token header (proving it is a legitimate request)
Sends the credentials as JSON payload. the username and password is the same one used to login to discuit. I do need to obfuscate them but hey-ho
Content-Type set to application/json

The output is then your profile details
```
echo $login_response | jq -r
```
So once you have a login sorted you can post content

I post to Cricket, so first of all I have to build the content in Markdown in a JSON format (I am officially a Masochist). At this point it is probably worth noting that ChatGPT\Claude\CoPilot is your friend. It takes the drudgery out of getting this bit right.

so the payload is:
```
{
    "type": "text",                    // Post type (text vs image/link)
    "title": "CricBuzz News Summary — 2025-08-27",  // Post title
    "body": "### Story 1\nContent...",              // Markdown content
    "community": "Cricket"                          // Target community name
}
```
And once you have that sorted then the below will do the business
```
post_response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
    -b /tmp/cookies.txt \
    -H "Content-Type: application/json" \
    -H "X-Csrf-Token: $csrf_token" \
    -d "{\"type\":\"text\",\"title\":\"$title\",\"body\":\"$body\",\"community\":\"$COMMUNITY\"}" \
    "$DISCUIT_BASE/api/posts")
```
The key part is the "community": "Cricket" field in the JSON payload. This tells Discuit which community to post to.
The server checks if your authenticated user has permission to post to "Cricket"
If authorized, the post appears in that community

How does it work? I think this is the process

Firstly the server validates your session cookies, then it confirms you can post to the "Cricket" community.

Then comes CSRF Validation: Server verifies the CSRF token matches your session

Post Creation: Server creates the post and associates it with the "Cricket" community

Response: Server returns success/failure status and post details

I have written some error checking to stop duplicates and to ensure that the posts are formatted correctly. After all these years Markdown is somewhat of a new thing for me (LaTeX FTW lol)

I am more than happy to share my python attempts if anyone wants to pick them apart and do their own thing. I will sanitise them of course.

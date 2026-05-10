Relating to the improvements doc. Couple of points

I want the exact same theme and style. I imagine you’ll need to do this for both the form and chart sections. I suspect it will take longer than 15 hours to do all that.

-> If theme and style works for you then we don't have to port to shadcn, I suggested because I thought it was initially built for mvp but if we are okay with this theme and style no issues


Hydration issues: do we know the exact cause? How do we know that switching will solve it and not just reproduce. 

-> hydration error occurs in nextjs because it uses something called server side rendering but libraries like MUI make use of client side JS to make changes in few components, so on server we don't have access to window object and when that html comes to client and react renders it causes issue/


Apparently shadcn won’t provide a charting system. What will you use instead?, 

shadcn have charts internally they make use of recharts

https://ui.shadcn.com/docs/components/radix/chart 

 

What exactly feels slow and why? Does it come more our apis taking too long?,


nope, but is this just me, are you not facing similar issue on your end? 

I face it let say once all the data is in and charts are rendered, now when I am switching tabs 
between financial and retirement there is a lag. 


What kind of caching:,

LocalStorage?
    •    IndexedDB?
    •    URL state?
    •    Server session?
    •    React Query cache?
    •    Zustand persist?
    •    Redux persist?
Error handling: is this for the user or for us? How will it be useful? Remember the front end needs to run for the user,
Let’s update next js - and see what breaks,
Other than change in framework - how does this correct the architecture concerns you had?
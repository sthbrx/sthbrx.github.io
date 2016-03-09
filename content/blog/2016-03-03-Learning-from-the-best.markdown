Title:Learning From the Best
Authors: Callum Scarvell
Date: 2016/03/03
Category: Education
Tags:education, work experience, Linux Gods 

When I first started at IBM I knew how to alter Javascript and compile it. This is because of my many years playing Minecraft (yes I am a nerd). Now I have leveled up! I can understand and use Bash, Assembly, Python, Ruby and C! Writing full programs in any of these languages is a very difficult prospect but none the less achievable with what I know now. Whereas two weeks ago it would have been impossible. Working here even for a short time has been an amazing Learning experience for me, plus it looks great on a resume! Learning how to write C has been one of the most useful things I have learnt. I have already written programs for use both in and out of IBM. The first program I wrote was the standard newbie 'hello world' exercise. I have now expanded on that program so that it now says, "Hello world! This is Callum Scarvell". This is done using strings that recognise my name as a set character. Then I used a header file called conio.h or curses.h to recognise 'cal' as the short form of my name. This is so now I can abbreviate my name easier. Heres what the code looks like:

''' C
#include <stdio.h>
#include <string.h>
#include <curses.h>

int main() {
  printf("Hello, World! This Is cal");

char first_name[] = "Callum";
  char last_name[] = "Scarvell";
  char name[100];

  /* testing code */
  if (strncmp(first_name, "Callum", 100) != 0) return 1;
  if (strncmp(last_name, "Scarvell",100) != 0) return 1;
  
  last_name[0] = 'S';
  sprintf(name, "%s %s", first_name, last_name);
  if (strncmp(name, "Callum Scarvell", 100) == 0) {
      printf("This is %s\n",name);
  }
/*printf("actual string is -%s-\n",name);*/
  return 0;
}

void Name_Rec()
{
 int i,j,k;
 char a[30],b[30];

 clrscr();
 puts("Callum Scarvell : \n");
 gets(a);

 printf("\n\ncal : \n\n%c",a[0]);
 for(i=0;a[i]!='\0';i++)
'''

The last two lines have been left out to make it a challenge to recreate. Feel free to test your own knowledge of C to finish the program! My ultimate goal for this program is to make it generate the text 'Hello World! This is Callum Scarvell's computer. Everybody else beware!'(which is easy) then import it into the Linux kernel to the profile login screen. Then I will have my own unique copy of the kernel. And I could call myself an LSD(Linux system developer). That's just a small pet project I have been working on in my time here. Another pet project of mine is my own very altered copy of the open source game NetHack. It's written in C as well and is very easy to tinker with. I have been able to do things like set my characters starting hit points to 40, give my character awesome starting gear and keep save files even after the death of a character. These are just a couple small projects that made learning C so much easier and a lot more fun. And the whole time I was learning C, Ruby, or Python I had some of the best system developers in the world showing me the ropes. This made things even easier, and much more comprehensive. So really its no surprise that in three short weeks I managed to learn almost four different languages and how to run a blog from the raw source code. The knowledge given to me by the OzLabs team is priceless and invaluable. I will forever remember all the new faces and what they taught me. And the _Linux Gods_ will answer your prayers whether e-mail or in person because they walk among us! So if you ever get an opportunity to do work experience, internship or a graduate placement take the chance to do it because you will learn many things that are not taught in school.

If you would like to reveiw the source code for the blog or my work in general you can find me at [CallumScar.github.com](https://github.com/CallumScar) or find me on facebook, [Callum Scarvell](https://www.facebook.com/callum.scarvell/about). 
And a huge thankyou to the OzLabs team for taking me on for the three weeks and for teaching me so much! i am forever indebted to everyone here.   
